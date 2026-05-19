# Gestor de Torneos RFFM — Manual de Usuario

## Índice

1. [Descripción general](#1-descripción-general)
2. [Caso de uso típico](#2-caso-de-uso-típico)
3. [Acceso a la aplicación](#3-acceso-a-la-aplicación)
4. [Sidebar — Selección de torneo](#4-sidebar--selección-de-torneo)
5. [Dashboard — Gestión de equipos](#5-dashboard--gestión-de-equipos)
6. [Configurador — Fases y grupos](#6-configurador--fases-y-grupos)
7. [Cuadro Visual — Asignación de equipos](#7-cuadro-visual--asignación-de-equipos)
8. [Partidos — Calendario y resultados](#8-partidos--calendario-y-resultados)
9. [Agenda — Vista multi-torneo](#9-agenda--vista-multi-torneo)
10. [Sorteo](#10-sorteo)
11. [Ajustes](#11-ajustes)
12. [Vistas públicas](#12-vistas-públicas)
13. [Bracket Gestión (bracket.html)](#13-bracket-gestión-brackethtml)
14. [Preguntas frecuentes](#14-preguntas-frecuentes)

---

## 1. Descripción general

El **Gestor de Torneos RFFM** es una aplicación web interna para organizar torneos de Fútbol 7. Permite:

- Crear torneos con múltiples fases (grupos, semifinales, final…).
- Gestionar los equipos participantes y sus escudos.
- Configurar la progresión automática entre fases (quién avanza de cada grupo).
- Generar y editar el calendario de partidos.
- Realizar el sorteo de grupos en tiempo real.
- Publicar un bracket visual de solo lectura para el público.
- Controlar qué torneos son visibles en el menú público.

**Tecnología:** Streamlit (Python) + Supabase (base de datos y almacenamiento de imágenes).

---

## 2. Caso de uso típico

A continuación se describe el flujo completo para organizar un torneo de Fútbol 7 con fase de grupos y eliminatorias.

### Paso 0 — Antes de empezar

Reúne la información necesaria:
- Lista de equipos participantes (nombre, competición de origen, escudo si lo tienes).
- Formato del torneo: número de grupos, equipos por grupo, cuántos avanzan.
- Fechas, horas y campos de juego.

### Paso 1 — Crear el torneo

1. En el sidebar, despliega **➕ Nuevo torneo**.
2. Escribe el nombre (p.ej. *Torneo Campeones 2026*) y una descripción opcional.
3. Pulsa **Crear**.
4. Selecciona el torneo recién creado en el selector del sidebar.

### Paso 2 — Cargar los equipos

1. Ve a **Dashboard**.
2. Pulsa **Añadir equipos** → se abre el modal de importación masiva.
3. Descarga la plantilla CSV si la necesitas, rellénala con los datos de los equipos y súbela.
4. Revisa la vista previa y confirma. Los equipos nuevos se crean; los que ya existían se actualizan por nombre.
5. Para editar un equipo individual (nombre, escudo, competición), haz clic en la tarjeta del equipo.

### Paso 3 — Configurar las fases

1. Ve a **Configurador**.
2. Crea la **Fase de grupos** (orden 1): define cuántos grupos y cuántos equipos por grupo.
3. Si hay eliminatorias, crea **Semifinales** (orden 2), **Final** (orden 3), etc.
4. Para cada fase de eliminación, configura la **progresión**: qué posición de cada grupo de fase anterior alimenta cada plaza de los grupos de la siguiente fase.
5. Ajusta el **orden visual** de los grupos en el bracket si lo necesitas.

### Paso 4 — Sorteo

1. Ve a **Sorteo**.
2. Selecciona la fase de grupos.
3. Distribuye los equipos en los grupos (manualmente o con ayuda del sorteo visual).
4. El resultado queda guardado y es visible en el Cuadro Visual y el Bracket Vista.

### Paso 5 — Generar el calendario

1. Ve a **Partidos**.
2. Selecciona la fase de grupos.
3. Pulsa **⚡ Generar partidos**. Se crean automáticamente todos los enfrentamientos (ida o ida y vuelta según la configuración).
4. Rellena las fechas, horas y campos en la tabla editable. Pulsa **Guardar cambios**.

### Paso 6 — Publicar el bracket

1. Ve a **Ajustes**.
2. Activa el toggle **Mostrar en el menú público del Bracket Vista**.
3. Comparte la URL del Bracket Vista o el código QR con el público.

### Paso 7 — Introducir resultados

Durante el torneo, en **Partidos**:
- Introduce los goles de local y visitante en las columnas *Goles L* y *Goles V*.
- Pulsa **Guardar cambios**. El bracket se actualiza en tiempo real.

### Paso 8 — Fase eliminatoria

1. Una vez terminada la fase de grupos, ve a **Cuadro Visual** → selecciona la fase de semifinales.
2. Los equipos clasificados aparecen disponibles para ser asignados a sus plazas según la configuración de progresión.
3. Genera los partidos de semifinales en **Partidos**.
4. Repite hasta la final.

---

## 3. Acceso a la aplicación

| Vista | URL | Acceso |
|---|---|---|
| Administración | URL interna de Streamlit | Solo staff con credenciales |
| Bracket Gestión | `bracket.html?torneo=ID` | Solo staff |
| Bracket Vista (público) | `bracket-view.html?torneo=ID` | Público sin contraseña |
| Menú público de torneos | `bracket-view.html` (sin parámetro) | Público |
| Cabeceras de grupos | `grupos-info.html?torneo=ID` | Público |

---

## 4. Sidebar — Selección de torneo

El sidebar izquierdo es el punto de partida para todo.

**Selector de torneo:** desplegable con todos los torneos existentes. Seleccionando uno, todas las secciones del menú trabajan sobre ese torneo.

**➕ Nuevo torneo:** expander para crear un torneo nuevo. Campos:
- *Nombre* — obligatorio.
- *Descripción* — opcional, aparece en el menú público del bracket.

**QR Cuadro Visual:** expander con el QR que apunta al menú público de todos los brackets. Útil para proyectar o imprimir.

---

## 5. Dashboard — Gestión de equipos

Vista principal para administrar los equipos del torneo seleccionado.

### Métricas superiores

- **Total Equipos** — número de equipos registrados.
- **En Competición** — equipos activos (no eliminados).

### Añadir equipos (importación masiva)

Pulsa **Añadir equipos** para abrir el modal de importación. Acepta archivos **Excel (.xlsx)** o **CSV (.csv)**.

**Columnas del archivo:**

| Columna | Obligatorio | Descripción |
|---|---|---|
| `nombre` | ✅ Sí | Nombre del equipo |
| `escudo_url` | ❌ No | URL pública de la imagen del escudo |
| `competicion` | ❌ No | Competición de procedencia |
| `grupo` | ❌ No | Grupo de la competición de origen |

- La primera fila debe ser la cabecera con esos nombres exactos (en minúsculas).
- Si un equipo ya existe (mismo nombre), **solo se actualizan los campos que vengan rellenos**; los vacíos conservan el valor actual.
- Si el equipo no existe, se crea nuevo.

Descarga la **plantilla CSV** desde el propio modal como referencia.

### Tarjetas de sorteo (PDF)

Pulsa **🖨️ Tarjetas sorteo** para generar un PDF con una tarjeta por equipo (nombre y escudo), listo para imprimir y usar en el sorteo presencial.

### Plantilla de equipos

Muestra todas las tarjetas de equipos. Usa el buscador para filtrar por nombre.

**Editar un equipo:** haz clic en la tarjeta del equipo. Se abre un modal con:
- *Nombre del equipo* — editable.
- *URL del escudo* — pega una URL pública de imagen.
- *O sube una imagen directamente* — sube un fichero PNG, JPG, WEBP o SVG desde tu ordenador. La imagen se sube al almacenamiento de Supabase y se guarda como URL automáticamente. Si subes un fichero, tiene prioridad sobre la URL escrita.
- *Competición* y *Grupo* — datos informativos de origen.

> **Nota:** URL y fichero conviven. Si solo tienes URL, usa el campo de texto. Si tienes el fichero del escudo, súbelo directamente y el sistema lo gestiona.

---

## 6. Configurador — Fases y grupos

Define la estructura del torneo: cuántas fases tiene, cuántos grupos por fase y cuántos equipos por grupo.

### Crear una fase

Despliega **➕ Crear Nueva Fase**:
- *Nombre de la fase* — p.ej. *Fase de grupos*, *Semifinales*, *Final*.
- *Orden* — número que determina la secuencia (1 = primera fase, 2 = segunda, etc.).

### Seleccionar fase a configurar

El selector muestra todas las fases del torneo. Al seleccionar una:

**Toggle "Ocultar en bracket":** actívalo para que esta fase no aparezca en el Bracket Vista público (aunque sigue siendo visible en el Bracket Gestión). Útil para ocultar las fases de semifinales/final mientras no han comenzado.

> **Importante:** aunque una fase esté oculta, los bordes de colores (verde/gris) en la clasificación de grupos sí tienen en cuenta su configuración de progresión. Los espectadores ven qué equipos avanzan aunque la fase de destino esté oculta.

**Formato de partidos:** elige entre *Ida (1 partido)* o *Ida y vuelta (2 partidos)* por enfrentamiento. Si ya existen partidos generados, cambiar el formato muestra un aviso para regenerar.

### Añadir grupos

Indica cuántos grupos añadir y cuántos equipos por grupo, luego pulsa **Añadir**.

### Orden y nombres en el cuadro visual (Fase 1)

En la fase 1, despliega el expander **Orden y nombres en el cuadro visual**. Aquí puedes:
- Renombrar cada grupo.
- Cambiar el número de equipos.
- Asignar una **Posición** (número entero) para controlar el orden de aparición en el bracket visual. Los grupos sin posición asignada van al final.

Pulsa **Guardar cambios** para confirmar.

### Configurar progresión (fases 2 en adelante)

Para semifinales, final u otras fases de eliminación, la interfaz muestra la **configuración de progresión visual**: una tabla donde se asigna qué posición de qué grupo de la fase anterior ocupa cada plaza de cada grupo de esta fase.

Ejemplo: *"La plaza 1 de Semifinal 1 la ocupa el 1º del Grupo A"*.

### Eliminar un grupo

Despliega **🗑️ Eliminar un grupo**. Cada grupo tiene su botón de borrado con confirmación. Al eliminar un grupo se eliminan también sus participantes.

---

## 7. Cuadro Visual — Asignación de equipos

Permite asignar equipos concretos a las plazas de cada grupo.

### Fase 1 (grupos iniciales — Sorteo)

Muestra los grupos en tarjetas. Cada plaza vacía tiene un selector con los equipos libres (no asignados a ningún grupo). Selecciona el equipo y se guarda automáticamente.

Para hacer el sorteo de forma aleatoria o asistida, usa la sección **Sorteo** del menú.

### Fases de progresión (semifinales, final…)

Muestra los grupos de la fase seleccionada junto con los clasificados disponibles de la fase anterior. Arrastra o selecciona para asignar los clasificados a sus plazas.

> Si ya se generaron partidos para esta fase y se modifican equipos, la app avisa de que hay que ir a **Partidos** y regenerar el calendario.

---

## 8. Partidos — Calendario y resultados

Gestiona el calendario de partidos y la introducción de resultados.

### Seleccionar fase

El selector muestra todas las fases del torneo. Elige la que quieras gestionar.

### Generar / Regenerar partidos

- **⚡ Generar partidos** — crea todos los partidos de la fase (todos contra todos dentro de cada grupo, en el formato de vueltas configurado). Solo aparece si no hay partidos generados.
- **🔄 Regenerar partidos** — borra los partidos existentes y los vuelve a crear. Pide confirmación. Útil si se han cambiado equipos o grupos.
- **🔗 Sincronizar equipos** — actualiza los partidos ya generados con los equipos reales que han ocupado sus plazas tras el sorteo. No borra ni regenera, solo actualiza los nombres.

### Filtrar por campo

El campo de filtro (esquina superior derecha) permite ver solo los partidos de un campo concreto.

### Tabla editable por grupo

Los partidos se muestran agrupados por grupo, en un expander por cada uno. La tabla permite editar:

| Columna | Descripción |
|---|---|
| Jornada | Número de jornada dentro del grupo |
| Local / Visitante | Solo lectura (se cambian con "Invertir") |
| Fecha | Fecha del partido (DD/MM/YYYY) |
| Hora | Hora de inicio (HH:MM) |
| Campo | Nombre o número del campo |
| Goles L | Goles del equipo local |
| Goles V | Goles del equipo visitante |
| Invertir ⇅ | Marca la casilla para intercambiar local y visitante al guardar |
| 🗑️ | Marca la casilla para **eliminar** ese partido al guardar |

Pulsa **Guardar cambios** en cada grupo para confirmar. Los partidos marcados con 🗑️ se eliminan; el resto se actualiza.

> **Consejo:** para eliminar un partido puntual (p.ej. uno generado por error), marca su casilla 🗑️ y guarda. No necesitas regenerar toda la fase.

---

## 9. Agenda — Vista multi-torneo

Muestra todos los partidos de todos los torneos para una fecha concreta, con filtros por campo y torneo.

Útil para gestionar la logística del día: ver qué partidos hay en cada campo a cada hora, independientemente del torneo al que pertenezcan.

---

## 10. Sorteo

Permite realizar el sorteo de equipos en los grupos de forma asistida o manual.

- Muestra los grupos vacíos y la bolsa de equipos disponibles.
- Puedes asignar equipos uno a uno, o usar el modo aleatorio para distribuirlos automáticamente.
- El resultado del sorteo queda guardado en el Cuadro Visual.
- Para el sorteo presencial, imprime las **tarjetas de sorteo** desde el Dashboard.

---

## 11. Ajustes

Configuración general del torneo seleccionado.

### Accesos

Tarjetas con los enlaces rápidos a cada vista del torneo:
- **Bracket Gestión** — edición de resultados y grupos (uso interno).
- **Bracket Vista** — vista pública de solo lectura.
- **Cabeceras Grupos** — árbol de grupos con nombre y notas.
- **Vista TV** — pantalla de sorteo en tiempo real (si hay grupos configurados).

Cada tarjeta tiene dos botones:
- **🔗 URL y QR** — muestra la URL completa y un código QR descargable con el logo RFFM incrustado.
- **↗ Abrir** — abre la vista directamente en una pestaña nueva.

### Visibilidad

**Toggle "Mostrar en el menú público del Bracket Vista":**
- Activado (por defecto) → el torneo aparece en el menú público de `bracket-view.html`.
- Desactivado → el torneo no aparece en el menú. Útil para torneos en preparación o ya finalizados que no quieres mostrar.

> El torneo sigue siendo accesible por URL directa (`bracket-view.html?torneo=ID`) aunque esté oculto del menú.

### Zona de peligro

**🗑️ Eliminar torneo** — elimina el torneo y **todos** sus datos en cascada: fases, grupos, participantes, partidos y equipos. Requiere confirmación explícita. Esta acción **no se puede deshacer**.

---

## 12. Vistas públicas

### bracket-view.html — Bracket Vista (menú y vista)

Acceso sin contraseña, pensado para el público y para proyectar en pantallas.

**Sin parámetro (`bracket-view.html`):** muestra el menú de torneos públicos (aquellos con *Mostrar en menú público* activado en Ajustes). Al pulsar un torneo se va a su bracket.

**Con parámetro (`bracket-view.html?torneo=ID`):** muestra directamente el bracket de ese torneo.

**Funcionalidades del bracket visual:**
- Si el torneo tiene un solo grupo, va directamente al detalle del grupo (clasificación y partidos).
- Si hay varios grupos, muestra el cuadro completo con conectores entre fases.
- Los grupos con más de 2 equipos muestran la clasificación con **bordes de colores**:
  - Verde → posición que avanza a la siguiente fase.
  - Gris → posición que no avanza.
  - Los bordes se muestran aunque la fase de destino esté oculta.
- Al pulsar en cualquier grupo se abre el **detalle** con clasificación completa y lista de partidos.
- El bracket se escala automáticamente para ocupar el ancho de pantalla disponible.
- Botón **↓ Guardar imagen** para exportar el bracket como PNG.

### grupos-info.html — Cabeceras de grupos

Vista pública con el árbol de grupos del torneo: nombre, notas y estructura. Sin clasificaciones ni resultados.

---

## 13. Bracket Gestión (bracket.html)

Vista interna (requiere credenciales) para editar resultados directamente en el bracket visual:
- Haz clic en cualquier partido para editar el resultado.
- Los conectores entre grupos se dibujan automáticamente según la configuración de progresión.
- Muestra todas las fases, incluidas las ocultas en el Bracket Vista público.
- Misma lógica de bordes verde/gris en las clasificaciones de grupos.

---

## 14. Preguntas frecuentes

**¿Puedo cambiar el nombre de un grupo después de generarlo?**
Sí, en Configurador → expander *Orden y nombres en el cuadro visual* (Fase 1) o directamente en la configuración de progresión para fases posteriores.

**¿Qué pasa si cambio equipos después de generar partidos?**
Los partidos ya generados no se actualizan automáticamente. Usa **🔗 Sincronizar equipos** para actualizar los nombres sin regenerar, o **🔄 Regenerar partidos** si quieres rehacer el calendario completo.

**¿Puedo eliminar un partido suelto sin borrar toda la fase?**
Sí. En la tabla de partidos, marca la casilla 🗑️ de ese partido y pulsa **Guardar cambios**.

**¿Cómo subo el escudo de un equipo si tengo el fichero en mi ordenador?**
Edita el equipo desde el Dashboard, pulsa en la tarjeta del equipo y usa el campo **"O sube una imagen directamente"**. La imagen se sube a Supabase Storage y se guarda como URL automáticamente.

**¿Puedo usar URL y fichero para los escudos a la vez?**
Sí, conviven. Cada equipo puede tener su escudo como URL externa o como fichero subido al almacenamiento; ambos funcionan igual en el bracket y la clasificación.

**¿Cómo controlo qué torneos ve el público en el menú del bracket?**
En Ajustes, activa o desactiva el toggle **"Mostrar en el menú público del Bracket Vista"** para cada torneo.

**¿Las fases ocultas afectan a los bordes verdes/grises de la clasificación?**
No. Los bordes de color tienen en cuenta la configuración de progresión de todas las fases, estén ocultas o no. El público ve qué posiciones avanzan aunque la fase de destino no sea visible todavía.

**¿Puedo tener el mismo equipo en dos grupos?**
No. Cada equipo solo puede estar asignado a un grupo por torneo.

**¿Qué es el orden en el bracket y cómo funciona?**
El campo *Posición* en el configurador determina el orden visual de los grupos en el bracket (de arriba a abajo dentro de su columna). El valor más bajo aparece primero. Grupos sin posición asignada van al final, ordenados por nombre. Esto aplica a todas las fases, no solo a la primera.
