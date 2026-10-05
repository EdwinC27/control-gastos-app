# Control de Gastos

Aplicación web personal para llevar el control de ingresos y gastos mensuales.
Corre en tu propia computadora, guarda todo en archivos CSV dentro de `data/`
y no manda nada a internet.

Está pensada para responder tres preguntas:

- **¿Cómo voy este mes?** Ingresos, gastos, disponible y estado financiero.
- **¿Qué ya pagué y qué me falta juntar?** Un checklist por mes.
- **¿Cuándo termino de pagar cada cosa?** Seguimiento de pagos a plazos.

---

## Cómo arrancarla

Necesitas Python 3.10 o superior.

**La primera vez**, instala las dependencias:

```bash
pip install -r requirements.txt
```

**Cada vez que la quieras usar**, desde la carpeta del proyecto:

```bash
python app.py
```

Y abre en el navegador:

```
http://127.0.0.1:2004
```

Para cerrarla, `Ctrl + C` en la terminal.

> La app se recarga sola cuando cambias un archivo del código, así que no hace
> falta reiniciarla mientras editas.

### Dejarla corriendo sola

Si no quieres abrir la terminal cada vez, instálala como tarea de Windows:
arranca sola al iniciar sesión, sin ventana, en el mismo puerto 2004.

```powershell
powershell -ExecutionPolicy Bypass -File .\servicio\instalar.ps1
```

Eso hace tres cosas: crea la tarea programada **Control de Gastos** (se reinicia
sola si se cae), deja un acceso directo con el icono de la app en tu escritorio,
y la arranca en ese momento. No pide permisos de administrador.

Para quitarlo todo:

```powershell
powershell -ExecutionPolicy Bypass -File .\servicio\desinstalar.ps1
```

Corriendo así no hay consola donde ver errores: todo queda en
`data/servidor.log`. Y como la tarea usa `servidor.py` en vez de `app.py`, no
recarga al cambiar el código — si editas algo, reinicia la tarea desde el
Programador de tareas o corre el desinstalador y el instalador otra vez.

---

## Guía rápida de uso

### 1. Registra tus ingresos

**Ingresos → Agregar ingreso.** Concepto, monto y frecuencia:

| Frecuencia | Se cuenta… |
|---|---|
| Mensual | todos los meses mientras esté activo |
| Anual | una vez al año, en el mes de la fecha de inicio |
| Único | solo en el mes y año de la fecha de inicio |

La *fecha de finalización* es opcional: después de ese mes deja de contarse.

### 2. Registra tus gastos

**Gastos → Agregar gasto.** Igual que los ingresos, más:

- **Categoría** — para el desglose del dashboard.
- **Tipo** — fijo (recurrente) o extraordinario (no recurrente).
- **Número de pagos** *(opcional)* — para lo que pagas a plazos.

### 3. Pagos a plazos

Si un gasto tiene fin (un terreno a 48 mensualidades, un mueble a 12 meses),
escribe cuántos pagos son en **Número de pagos** y deja la fecha de
finalización vacía: la app la calcula sola.

Ejemplo: $5,500 mensuales, 48 pagos, primer pago 01/10/2026
→ último pago **septiembre 2030**, costo total $264,000.

En el dashboard, la sección **Pagos a plazos** te muestra de cada uno:
el avance (`17 de 48 pagos`), el mes del último pago, cuántos te faltan y el
saldo pendiente. Los pagos hechos se cuentan solos, por fecha: no tienes que
marcar nada.

### 4. Marca lo que ya pagaste (planeado vs. real)

En el dashboard, la tabla **Gastos del mes** tiene tres botones por renglón:

| Botón | Significa |
|---|---|
| ⭕ Falta por juntar | todavía no tienes ese dinero |
| 🏦 Apartado | ya lo separaste completo, pero no lo has pagado |
| ✅ Pagado | ya salió |

La columna **Ya juntado / usado** cambia según el estado del gasto:

**Si falta por juntar**, registras *abonos*. Un gasto de $12,000 del que esta
quincena juntaste $1,000: escribes `1000`, le pones una nota si quieres
(«quincena del 15», «venta de la bici») y pulsas **+**. La fila muestra
`$1,000.00 · falta $11,000.00` con su barra de avance. Cuando los abonos
completan el monto, el gasto pasa solo a **Apartado**.

**Si ya está apartado**, el dinero ya lo tienes, así que ahora registras *usos*:
cuánto ocupaste y en qué. La gasolina de $4,000 que ya apartaste y de la que
cargaste $600 el martes se ve como `Usado $600.00 · quedan $3,400.00`. El gasto
sigue contando como apartado: esto solo te dice a dónde se fue el dinero.

**Si ya está pagado**, no hay nada que registrar: la celda dice «Completo».

Cada movimiento guarda solo su fecha y hora. Bajo el formulario aparece el
enlace **«3 movimientos →»**, que te lleva a la pestaña **Movimientos** ya
filtrada por ese gasto.

### 6. La pestaña Movimientos

Todos los abonos y usos del mes en un solo lugar: cuánto llevas abonado, cuánto
usado y la lista completa con fecha, hora, gasto, categoría, tipo, monto y nota.

Puedes **buscar** por concepto o nota, **filtrar** por tipo (abono / uso) y por
categoría, **ordenar** por cualquier columna, **borrar** un movimiento suelto y
**registrar** uno nuevo desde ahí mismo: eliges el gasto del mes, el monto y la
nota. Para corregir un error, registra el mismo movimiento con monto negativo.

El **tipo no se elige**: lo deduce el estado del gasto —si falta por juntar es
un abono, si ya está apartado es un uso— y te lo muestra antes de guardar. Los
gastos ya pagados no aparecen en la lista, porque no hay nada que registrarles.

Arriba, la tarjeta **Pagos del mes** suma las cuatro columnas —pagado,
apartado, abonado y lo que **falta por juntar**— y, si ya usaste parte del
dinero apartado, te dice cuánto llevas usado y cuánto queda. También hay atajos para *marcar todo como pagado* o
*reiniciar el mes*.

Esto no cambia los totales del dashboard: los gastos siguen contando completos.
Es solo para saber por dónde vas.

Cada mes lleva su propio registro, así que al cambiar de mes empiezas limpio.

### 7. Estado financiero

Se calcula con el porcentaje de tu ingreso que te queda disponible:

| Estado | Disponible | Color de la barra |
|---|---|---|
| Positivo | 15% o más | verde |
| Equilibrado | entre 5% y 15% | amarillo |
| Déficit | menos del 5% (o negativo) | rojo |

La barra de **ingreso comprometido** usa esos mismos colores.

### 8. Tus categorías

**Categorías** en el menú lateral. Ahí puedes:

- **Agregar** una nueva (aparece de inmediato en el formulario de gastos).
- **Renombrar** una: se actualizan solos todos los gastos que la usaban.
- **Ocultar** una: deja de ofrecerse al capturar, pero los gastos que ya la
  tienen la conservan.
- **Eliminar** una: solo si ningún gasto la usa.

No hay que tocar el código para nada de esto.

### 9. Trabajar con las tablas

En **Gastos** e **Ingresos**:

- **Buscar** por concepto, categoría o notas.
- **Filtrar** por categoría, tipo, estado o si es a plazos.
- **Ordenar** haciendo clic en el título de cualquier columna (otra vez para
  invertir el orden).
- **⏸️ / ▶️** activa o desactiva un registro sin entrar a editarlo. Un registro
  inactivo no cuenta en ningún mes.
- **📋** duplica un gasto y te lleva directo a editar la copia.

### 10. Otros detalles

- **Modo oscuro**: botón abajo a la izquierda. Se recuerda entre sesiones.
- **Navegar entre meses**: flechas ← → arriba del dashboard, o el selector de
  mes y año. «Este mes» te regresa al actual.

---

## Dónde viven los datos

```
data/
├── gastos.csv        tus gastos
├── ingresos.csv      tus ingresos
├── categorias.csv    el catálogo de categorías
├── pagos.csv         estado de cada gasto (pagado/apartado), por mes
├── movimientos.csv   abonos y usos, con monto, nota, fecha y hora
└── backups/          respaldo automático diario (últimos 30 días)
```

Son CSV normales: los puedes abrir en Excel. Los encabezados están en inglés
(`concept`, `category`, `amount`, `type`, `frequency`, `start_date`, `end_date`,
`installments`, `active`, `notes`), igual que el código. La primera vez que se
modifica un archivo cada día se guarda una copia en `backups/`, por si algo
sale mal.

> **Ojo:** si dejas un CSV abierto en Excel, Windows lo bloquea y la app no
> podrá guardar. Te avisa con un mensaje; ciérralo y vuelve a intentar.

---

## Estructura del proyecto

```
control_gastos/
├── app.py           arranque de la app y dashboard
├── servidor.py      arranque en segundo plano, sin recarga y con log
├── servicio/        scripts para instalarla como tarea de Windows
├── common.py        lógica compartida: CSV, validaciones, plazos, filtros
├── expenses.py      rutas de gastos
├── income.py        rutas de ingresos
├── payments.py      marcar pagado / apartado / pendiente y registrar movimientos
├── movements.py     la pestaña de abonos y usos del mes
├── categories.py    administrar el catálogo de categorías
├── templates/       plantillas HTML (Jinja2)
├── static/          estilos, JavaScript e iconos de la app
└── data/            tus datos
```

Hecho con FastAPI, Jinja2 y Chart.js.
