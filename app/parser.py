import xml.etree.ElementTree as ET

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}

# Mapa NUTS2 → nombre de CCAA
NUTS2_CCAA = {
    "ES11": "Galicia",
    "ES12": "Principado de Asturias",
    "ES13": "Cantabria",
    "ES21": "País Vasco",
    "ES22": "Comunidad Foral de Navarra",
    "ES23": "La Rioja",
    "ES24": "Aragón",
    "ES30": "Comunidad de Madrid",
    "ES41": "Castilla y León",
    "ES42": "Castilla-La Mancha",
    "ES43": "Extremadura",
    "ES51": "Cataluña",
    "ES52": "Comunidad Valenciana",
    "ES53": "Illes Balears",
    "ES61": "Andalucía",
    "ES62": "Región de Murcia",
    "ES63": "Ciudad Autónoma de Ceuta",
    "ES64": "Ciudad Autónoma de Melilla",
    "ES70": "Canarias",
}

# NUTS1 con correspondencia directa a una sola CCAA
NUTS1_CCAA = {
    "ES3": "Comunidad de Madrid",
    "ES7": "Canarias",
}

CCAA = set(NUTS2_CCAA.values())


def text(element, xpath):
    node = element.find(xpath, NS)
    return node.text.strip() if node is not None and node.text else None


def extract_pais(status):
    loc = status.find("cac:ProcurementProject/cac:RealizedLocation", NS)
    if loc is None:
        return "España"
    country_code = loc.find("cac:Address/cac:Country/cbc:IdentificationCode", NS)
    if country_code is not None and country_code.text and country_code.text.strip().upper() not in ("ES", ""):
        country_name = loc.find("cac:Address/cac:Country/cbc:Name", NS)
        if country_name is not None and country_name.text:
            return country_name.text.strip()
        return country_code.text.strip()
    return "España"


def extract_comunidad(status):
    loc = status.find("cac:ProcurementProject/cac:RealizedLocation", NS)

    # Contratos en el extranjero: detección temprana por código de país
    if loc is not None:
        country_code = loc.find("cac:Address/cac:Country/cbc:IdentificationCode", NS)
        if country_code is not None and country_code.text and country_code.text.strip().upper() not in ("ES", ""):
            return "Extranjero"

    # Fuente primaria: cadena ParentLocatedParty del órgano de contratación.
    # Más fiable que RealizedLocation porque refleja la adscripción institucional
    # del órgano y no varía entre actualizaciones del mismo expediente.
    located = status.find(".//cac-place-ext:LocatedContractingParty", NS)
    if located is not None:
        parent = located.find("cac-place-ext:ParentLocatedParty", NS)
        chain = []
        while parent is not None:
            node = parent.find("cac:PartyName/cbc:Name", NS)
            if node is not None and node.text:
                chain.append(node.text.strip())
            parent = parent.find("cac-place-ext:ParentLocatedParty", NS)
        for name in chain:
            if name in CCAA:
                return name

    # Fallback: RealizedLocation > CountrySubentityCode (NUTS)
    # Usado cuando el órgano no tiene CCAA en su jerarquía (organismos nacionales, etc.)
    if loc is not None:
        code_node = loc.find("cbc:CountrySubentityCode", NS)
        if code_node is not None and code_node.text:
            code = code_node.text.strip()

            if code.upper() in ("ES", "ESPAÑA", "ESPANA"):
                return "Todo el territorio"

            if code.startswith("ESZ"):
                return "Extra-Regio"

            nuts2 = code[:4]
            ccaa = NUTS2_CCAA.get(nuts2)
            if ccaa:
                return ccaa

            nuts1 = code[:3]
            ccaa = NUTS1_CCAA.get(nuts1)
            if ccaa:
                return ccaa

    return None


def _parse_entries(root):
    results = []
    for entry in root.findall("atom:entry", NS):
        status = entry.find("cac-place-ext:ContractFolderStatus", NS)
        if status is None:
            continue

        link_node = entry.find("atom:link", NS)
        url = link_node.get("href") if link_node is not None else None

        atom_id_node = entry.find("atom:id", NS)
        atom_id = atom_id_node.text.strip() if atom_id_node is not None and atom_id_node.text else None

        presupuesto_text = text(status, ".//cac:BudgetAmount/cbc:TaxExclusiveAmount")

        results.append({
            "atom_id": atom_id,
            "expediente": text(status, "cbc:ContractFolderID"),
            "titulo": text(status, "cac:ProcurementProject/cbc:Name"),
            "organo_contratacion": text(status, ".//cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name"),
            "estado": text(status, "cbc-place-ext:ContractFolderStatusCode"),
            "presupuesto": float(presupuesto_text) if presupuesto_text else None,
            "fecha_publicacion": text(entry, "atom:updated"),
            "comunidad_autonoma": extract_comunidad(status),
            "pais": extract_pais(status),
            "url": url,
        })
    return results


def parse_atom_bytes(data: bytes):
    root = ET.fromstring(data)
    return _parse_entries(root)


def parse_atom_file(filepath):
    tree = ET.parse(filepath)
    return _parse_entries(tree.getroot())


if __name__ == "__main__":
    datos = parse_atom_file("data/licitacionesPerfilesContratanteCompleto3.atom")
    print(f"Licitaciones parseadas: {len(datos)}")
    if datos:
        for d in datos[:5]:
            print(f"  {d['expediente']} | {d['comunidad_autonoma']} | {d['estado']}")
