---
name: Preferencias de workflow y commits
description: Reglas sobre cómo hacer commits en LicitMap
type: feedback
originSessionId: 27d084a7-ae92-4885-bb9e-2824eb1ea0e6
---
Los commits nunca deben incluir co-author de Claude. Solo el usuario (ivisor) como autor.

**Why:** El usuario quiere ser el único autor registrado en el historial de git.

**How to apply:** Al crear commits, NO añadir la línea `Co-Authored-By: Claude ...`. Usar solo el mensaje de commit sin firmas adicionales.

---

Hacer commit cada vez que se implementa algo nuevo — no acumular cambios grandes sin commitear.

**Why:** El usuario lo pidió explícitamente para mantener un historial granular.

**How to apply:** Al terminar cada feature o fix significativo, crear un commit inmediatamente sin esperar a que el usuario lo pida.
