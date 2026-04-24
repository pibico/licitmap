---
name: Preferencias de diseño del usuario
description: Guías sobre paleta de colores, temas y decisiones estéticas en LicitMap
type: feedback
originSessionId: 27d084a7-ae92-4885-bb9e-2824eb1ea0e6
---
No usar Catppuccin — se descartó tras probarlo. La paleta propia "Stone/Slate" fue aprobada.

**Why:** Catppuccin no funcionó ni visualmente ni técnicamente (problemas de especificidad CSS con Bootstrap).

**How to apply:** Al proponer cambios de diseño, usar la paleta actual o ajustes sobre ella.

## Calibración de fondos (importante)
- Light demasiado blanco → aburrido. Demasiado crema → satura la vista. El punto justo es #f9f7f4: apenas perceptible.
- Dark demasiado negro → incómodo. Demasiado claro → plano y saturado. El punto justo es #20232b: grafito azulado con profundidad.
- El usuario es sensible a la saturación de color: preferir fondos neutros/sutiles sobre los expresivos.

## Iconos de acción
- Botones de ayuda/herramienta: usar icono semántico (ej. libro para CPV) con color de acento, no lupa genérica
- El color de acento en el icono mejora la visibilidad; opacidad reducida en reposo (0.75) y plena al hover/activo

## Preferencias generales
- Páginas interactivas y responsive
- Animaciones sutiles y funcionales (el toggle sol/luna con rebote fue bien recibido)
- Badges de estado: abreviación (PUB, ADJ...) en tabla, nombre completo en filtros
- Paginación arriba y abajo de la tabla con espaciado consistente
