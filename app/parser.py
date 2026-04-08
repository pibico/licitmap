import xml.etree.ElementTree as ET

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}

CCAA = {
    "Andalucía", "Aragón", "Principado de Asturias", "Illes Balears",
    "Canarias", "Cantabria", "Castilla y León", "Castilla-La Mancha",
    "Cataluña", "Comunidad Valenciana", "Extremadura", "Galicia",
    "Comunidad de Madrid", "Región de Murcia", "Comunidad Foral de Navarra",
    "País Vasco", "La Rioja", "Ciudad Autónoma de Ceuta",
    "Ciudad Autónoma de Melilla",
}


def text(element, xpath):
    node = element.find(xpath, NS)
    return node.text.strip() if node is not None and node.text else None


def extract_comunidad(status):
    located = status.find(".//cac-place-ext:LocatedContractingParty", NS)
    if located is None:
        return None
    parent = located.find("cac-place-ext:ParentLocatedParty", NS)
    chain = []
    while parent is not None:
        node = parent.find("cac:PartyName/cbc:Name", NS)
        if node is not None and node.text:
            chain.append(node.text.strip())
        parent = parent.find("cac-place-ext:ParentLocatedParty", NS)
    # Buscar la CCAA en la cadena
    for name in chain:
        if name in CCAA:
            return name
    return None


def _parse_entries(root):
    results = []
    for entry in root.findall("atom:entry", NS):
        status = entry.find("cac-place-ext:ContractFolderStatus", NS)
        if status is None:
            continue

        link_node = entry.find("atom:link", NS)
        url = link_node.get("href") if link_node is not None else None

        presupuesto_text = text(status, ".//cac:BudgetAmount/cbc:TaxExclusiveAmount")

        results.append({
            "expediente": text(status, "cbc:ContractFolderID"),
            "titulo": text(status, "cac:ProcurementProject/cbc:Name"),
            "organo_contratacion": text(status, ".//cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name"),
            "estado": text(status, "cbc-place-ext:ContractFolderStatusCode"),
            "presupuesto": float(presupuesto_text) if presupuesto_text else None,
            "fecha_publicacion": text(entry, "atom:updated"),
            "comunidad_autonoma": extract_comunidad(status),
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
