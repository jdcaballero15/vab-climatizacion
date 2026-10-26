# Decisiones pendientes

No se asume nada de lo que figura acá. Cómo se refleja en las historias:

- **Decisión abierta** (`Abierta`): las historias afectadas llevan `blocked_by: [D-0XX]` y no pueden pasar a `ready` hasta resolverla.
- **Propuesta vigente** (`Propuesta` o `Pospuesta`): las historias llevan `assumes: [D-0XX]`. Se pueden implementar sobre la propuesta, sabiendo que si cambia hay que retocarlas.

El índice [docs/stories/INDEX.md](../stories/INDEX.md) lista las historias bloqueadas por decisión.

| ID | Decisión | Quién resuelve | Estado | Afecta |
|---|---|---|---|---|
| D-001 | Conectividad en campo: ¿hace falta modo offline? | Cliente | **Abierta** | E05-09 a E05-11, ADR 0003 |
| D-002 | Identificación de equipos: código propio o por ubicación | Negocio | **Propuesta** | E03-03, E03-05, E04-12, E07-03, E07-09, E11-02, E11-06 |
| D-003 | Edición de catálogos en el sistema nuevo | Negocio | **Propuesta** | E02-01 a E02-06, E02-08 |
| D-004 | Datos exactos que necesita administración para facturar | Negocio | Pospuesta | E04-09 |
| D-005 | Revisión y aprobación en bloque: ¿acciones o estados? | Negocio | **Propuesta** | E04-08, E07-04, E07-05 |
| D-006 | Costo recurrente de hosting y cómo se informa al cliente | Dirección de MendoData | **Abierta** | E00-05 |
| D-007 | Método de inicio de sesión | Desarrollo y negocio | **Propuesta** | E01-01 |
| D-008 | Retención y texto legal de datos personales (DNI y firmas) | Negocio y asesoría legal | **Abierta** | E12-04 |
| D-009 | Proveedor de mail transaccional | Desarrollo | **Abierta** | E00-10 |
| D-010 | Formato y calidad de la exportación de Persat | Cliente y desarrollo | **Abierta** | E11-01 a E11-04 |
| D-011 | ¿La firma del cliente es obligatoria en todo cierre? | Negocio | **Propuesta** | E05-07, E06-04, E06-06 |
| D-012 | Cierre de los issues de historias terminadas | Desarrollo | **Propuesta** | `scripts/sync_stories.py`, plantilla de PR |

## Detalle

### D-001 Conectividad en campo

Los formularios del cliente se contradicen: "siempre hay señal" contra "a veces no, en cámaras frigoríficas, sótanos y zonas rurales". **Hay que preguntarle al cliente directamente.** No asumir ninguna respuesta.
Mientras tanto, la PWA se diseña con soporte offline (ADR 0003, provisional). Es la decisión más cara de equivocar, por eso conviene resolverla primero.

### D-002 Identificación de equipos

Contradicción en los formularios: "código propio" contra "por ubicación dentro del cliente". No es una cosa o la otra: se usan las dos, para fines distintos.

Lo que se sabe (relevamiento de Gonza con los datos de Persat):

- **La gente se refiere al equipo por su ubicación dentro del cliente** (por ejemplo "Habitación 12" u "Oficina planta alta"). Es lo que reconoce el técnico y el cliente pidió explícitamente que se vea así. En Persat, al cerrar una orden, el técnico describe el equipo a mano con ubicación, subtipo, marca y potencia.
- **Existe un código interno de VAB**, guardado en Persat en la columna de número de serie (no es el número de serie de fábrica). Se arma con un prefijo, el número de cliente y un correlativo del equipo dentro del cliente (por ejemplo `EA0012301` = cliente 00123, equipo 01). La intención es que sea único en toda la empresa, pero no está controlado: hay unos pocos códigos repetidos entre clientes distintos.
- **El código no tiene largo fijo.** La estructura real es `[EA|EH]` + sigla de sector (opcional) + número de cliente + correlativo:
  - `EA` es equipo de aire acondicionado y `EH` es heladera (hoy solo en un cliente).
  - Las siglas de sector (unas ocho distintas) aparecen solo en un cliente con planta industrial, por ejemplo `EAFAB` + número de cliente + correlativo. Se cree que son sectores de la planta, sin confirmar.
  - Hay dos excepciones de formato viejo: un cliente con `EACAB` + correlativo sin número de cliente y otro con `CLI-` + número de cliente + correlativo.
  - El correlativo empieza en 2 dígitos y pasa a 3 al superar 99 (el equipo 100 de un cliente lleva `100`, sin rellenar los anteriores). Hay clientes con más de 100 equipos y varios con más de 60.
  - El número de cliente dentro del código no tiene una cantidad fija de dígitos.
- **Persat trae unos 530 equipos de unos 55 clientes.** Algunas decenas no tienen ubicación, unos 20 no tienen ningún dato y ninguno tiene número de serie de fábrica.
- **En casi 9 de cada 10 reparaciones de Persat no se eligió el equipo cargado**: el técnico lo describió a mano. El caso "el equipo no está cargado" es frecuente.
- **Los equipos se mueven dentro del cliente**: existe el trabajo de reubicación de unidad condensadora o evaporadora.
- **El número de cliente de Persat es texto, no un número**: conviven una serie numérica de 5 dígitos y una serie `CLI-` + 5 dígitos, y hay algunos sueltos con otro formato o sin número.

*Propuesta*:

1. **Código interno (`internal_code`)**: identificador único en toda la empresa, obligatorio y generado por el sistema, nunca escrito a mano. Es texto libre: no se valida por largo ni por formato, porque los códigos migrados no son parejos.
   - **Equipos nuevos**: prefijo según el tipo de equipo (`EA` aire acondicionado, `EH` heladera) + dígitos del número de cliente + correlativo del equipo dentro del cliente, con mínimo 2 dígitos y sin tope (01 a 99, después 100, 101...). Sin sigla de sector hasta que el cliente confirme qué son.
   - **Unicidad**: la garantiza una restricción en la base, no el formato. Como los largos son variables, dos combinaciones distintas podrían dar el mismo texto; si el código generado ya existe, el sistema prueba el siguiente correlativo.
   - **Equipos migrados**: conservan su código de Persat tal cual, con el formato que tengan. A los códigos repetidos se les asigna uno nuevo en la migración y el viejo queda como referencia a Persat.
2. **Ubicación (`location_note`)**: obligatoria. Es lo que se muestra primero en listados, órdenes y comprobantes, junto con el tipo de equipo. Dentro de un mismo domicilio no hay unicidad: pueden existir dos equipos con la misma ubicación (por ejemplo, dos splits en el mismo salón) y los distingue el código.
3. **Alta con lo mínimo**: para dar de alta un equipo alcanza con ubicación y tipo de equipo. Marca, modelo, potencia y el resto son opcionales y administración los completa después.
4. **Mudanzas**: si un equipo cambia de ubicación dentro del cliente, se edita la ubicación. Conserva su código y su historial; no se crea un equipo nuevo.
5. **Migración**: los equipos de Persat sin ubicación se importan con la ubicación "Sin ubicación" y quedan en el informe de calidad (E11-04) para que administración la complete.

Consecuencias:

- El cliente necesita un **número de cliente** (`client.number`), porque forma parte del código. Es texto y único. En la migración se toma el número de Persat tal cual; los clientes sin número reciben uno nuevo. En los clientes nuevos lo asigna el sistema siguiendo la serie numérica (el siguiente al máximo).
- Que el técnico dé de alta un equipo desde la app no está en ninguna historia (E03-03 es de administración). Queda como pregunta abierta; si se confirma, va en una historia nueva. Según el relevamiento las cuadrillas siempre tienen señal (ver `D-001`), así que el código se puede generar en el momento.
- El QR por equipo (E99-01) sigue en el icebox; si vuelve, se apoya en el código interno.

Preguntas abiertas para el cliente:

- ¿Quién asigna hoy los códigos? ¿Hay etiquetas físicas pegadas en los equipos?
- ¿Un equipo puede pasar de un cliente a otro? Si pasa, la propuesta es que conserve el historial, pero hay que confirmarlo.
- ¿Las siglas como `FAB` son sectores de la planta? ¿Hay que seguir usándolas en los equipos nuevos de ese cliente?
- ¿Qué prefijo llevan los tipos de equipo que no son aire ni heladera (cámara de frío, freezer, otros)?
- ¿El técnico tiene que poder dar de alta un equipo que no encuentra en la lista?

### D-003 Edición de catálogos

La decisión original era sobre listas de SharePoint ("editables de las dos formas" con columnas de elección). En un sistema a medida **ese problema desaparece**: la única puerta de entrada es la app, con las mismas validaciones.
*Propuesta*: los catálogos y listas de referencia (tipos de trabajo, tareas, fallas, reparaciones, repuestos, plantillas) se editan solo desde la app de administración, con importación y exportación CSV para cargas masivas. El estado de la orden y todo lo que dispara automatizaciones solo cambia por la API.

### D-004 Datos para facturar

Se pospone. El modelo guarda número de factura y fecha de registro (`invoice_record`). Si administración necesita más (importe, condición de venta, CUIT), se agrega.

### D-005 Revisión y aprobación en bloque

El cliente definió siete estados y no incluye "Revisión" ni "Pendiente de aprobación". La propuesta técnica los muestra como pasos del circuito.
*Propuesta*: no son estados. Son acciones de administración: aprobar o devolver una orden Terminada, y aprobar un lote de órdenes generadas (campo `requires_approval`). Si el cliente prefiere verlos como estados, se agregan.

### D-006 Costo recurrente de hosting

Con Microsoft 365 no había costo de infraestructura. Con el sistema a medida hay un costo mensual en dólares. Hay que definir cómo se informa y se cobra al cliente (referencia con cotización y fecha, o dentro de un abono de soporte). Las cuentas quedan a nombre del cliente. **Este tema se gestiona fuera del repositorio.**

### D-007 Método de inicio de sesión

*Propuesta*: correo y contraseña con política mínima, sesión por JWT de corta duración con refresco, límite de intentos. Evaluar más adelante inicio con cuenta Microsoft o Google si el cliente lo pide.

### D-008 Datos personales

El sistema guarda nombre y DNI de quien firma, y la firma manuscrita. Definir: plazo de retención, derecho de acceso y supresión, aviso en el comprobante, y si hace falta registrar la base ante la autoridad de aplicación. Consultar a asesoría legal.

### D-009 Proveedor de mail

Para informe mensual y comprobantes. Candidatos: Resend, Brevo, Amazon SES. Criterios: entregabilidad, costo, dominio propio del cliente (SPF, DKIM).

### D-011 Obligatoriedad de la firma

Los formularios del cliente dicen que la firma es obligatoria al cerrar una orden. La propuesta técnica, en cambio, dice "firma del cliente, si corresponde" para las órdenes en el lugar, y la exige solo en retiro y devolución.
*Propuesta*: seguir lo que dicen los formularios (firma obligatoria en todo cierre, con nombre y DNI), y que negocio defina qué pasa si el cliente no está presente (por ejemplo, un motivo de ausencia predefinido). No se inventa una excepción hasta que se defina.

### D-010 Exportación de Persat

El cliente confirmó que es exportable. Falta ver el formato real (CSV, Excel), qué campos trae el historial de trabajos y la calidad de los datos (duplicados, equipos sin cliente, fechas). Pedir una muestra con datos anonimizados antes de diseñar la importación. **La muestra no se sube al repo.**

### D-012 Cierre de los issues de historias terminadas

Hoy ningún issue de historia se cierra solo. `sync_stories.py` actualiza la etiqueta `estado:hecha` pero, por diseño, nunca cierra issues. La plantilla de PR usa `Cierra #`, que GitHub no reconoce como palabra clave de cierre (solo acepta las de inglés, como `Closes` o `Fixes`). Resultado: E01-01 (#21), E01-02 (#22), E01-03 (#23) y E01-04 (#24) están terminadas y sus issues siguen abiertos, lo que ensucia la vista de issues abiertos como lista de trabajo pendiente.

Opciones:

1. **`Closes #` en la plantilla de PR**: el issue se cierra al mergear la PR en `main`. No sirve cuando una historia se entrega en varias PR (como E01-02): la primera PR cerraría el issue antes de tiempo, o hay que acordarse de ponerlo solo en la última.
2. **Que `sync_stories.py` cierre el issue cuando la historia pasa a `done`** (y lo reabra si vuelve a otro estado): el cierre queda atado al archivo de la historia, que ya es la fuente de verdad, y funciona igual con una o varias PR. Al correr por primera vez cerraría los issues de las historias ya terminadas.

*Propuesta*: opción 2. En la plantilla, cambiar `Cierra #` por `Relacionado #` para que no parezca que cierra algo. Si se aprueba, se implementa en una PR aparte que actualice el script, su docstring y la plantilla.
