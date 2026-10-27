# Documentación

| Carpeta | Contenido | Quién lo mantiene |
|---|---|---|
| [architecture/](architecture/overview.md) | Arquitectura, modelo de datos, máquina de estados, ADR | Desarrollo |
| [domain/](domain/alcance-fase-1.md) | Alcance, glosario, roles y permisos, decisiones pendientes | Negocio y desarrollo |
| [stories/](stories/README.md) | Historias de usuario por épica (fuente de verdad) | Negocio valida, desarrollo implementa |
| [workflow/](workflow/definition-of-done.md) | Definición de terminado, ciclo de una historia con tres puertas, trabajo con agentes de IA y [despliegue en Render](workflow/despliegue.md) | Desarrollo |
| [code-standards.md](code-standards.md) | Estándares de código normativos y cómo se hace cumplir cada uno | Desarrollo |
| [architecture/adr/](architecture/adr/README.md) | Registros de decisiones (plantilla `0000` e índice) | Desarrollo |

## Orden de lectura para quien llega nuevo

1. [Alcance de la Fase 1](domain/alcance-fase-1.md)
2. [Glosario](domain/glosario.md)
3. [Visión general de la arquitectura](architecture/overview.md)
4. [Máquina de estados de la OT](architecture/order-state-machine.md)
5. [Historias](stories/README.md)

## Reglas para los documentos

- Español. Sin guion largo, usar guion simple.
- Diagramas y modelos en texto (Mermaid, DBML) para que se versionen y se revisen en un PR.
- El resumen ejecutable de las reglas vive en [`../CLAUDE.md`](../CLAUDE.md), que todo agente carga al iniciar. Una decisión técnica nueva es un ADR nuevo, no una edición de uno viejo. Si cambia una decisión, el ADR anterior pasa a `Reemplazado por ADR XXXX`.
- Repositorio público: nada de datos reales, precios ni acuerdos comerciales.
