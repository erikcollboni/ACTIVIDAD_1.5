# ACTIVIDAD_1.5 - Algoritmo de Maekawa

Este proyecto implementa una simulación de un sistema distribuido que resuelve el problema de la **Exclusión Mutua** utilizando el **Algoritmo de Maekawa**. 

El objetivo es orquestar múltiples nodos que compiten por acceder a una Sección Crítica (CS), garantizando seguridad (solo uno entra a la vez), vivacidad (libre de interbloqueos) y equidad mediante relojes lógicos.

## 1. Descripción del Problema

El sistema simula un entorno con **N nodos** (definidos en la configuración) que operan de forma autónoma y comparten un recurso común.

### El Algoritmo de Maekawa
A diferencia de algoritmos centralizados o de difusión total (como Ricart-Agrawala), Maekawa reduce el tráfico de red permitiendo que un nodo obtenga acceso a la Sección Crítica solicitando permiso solo a un subconjunto de nodos llamado **Quorum** (o *Voting Set*).

El ciclo de vida de un nodo consiste en:
1.  **Solicitud (Request):** El nodo difunde un mensaje a su *Quorum* con una marca de tiempo lógica.
2.  **Votación (Voting):** Cada nodo receptor concede su voto a un solo solicitante a la vez, basándose en la prioridad del reloj lógico (menor timestamp gana).
3.  **Acceso (Critical Section):** El solicitante entra en la SC solo cuando ha recibido el voto ("Reply") de **todos** los miembros de su Quorum.
4.  **Liberación (Release):** Al salir, el nodo libera los votos, permitiendo que los nodos del Quorum voten por el siguiente en su cola de prioridad.

## 2. Diseño de la Solución

La solución estructura cada nodo como una entidad independiente compuesta por tres hilos principales que gestionan la lógica de negocio, la escucha de mensajes y el envío de peticiones.

### Estructura del Código

* **Gestión de Quorums (Estrategia Grid):**
    Para asegurar la propiedad de intersección (necesaria en Maekawa), los nodos se organizan lógicamente en una cuadrícula de $\sqrt{N} \times \sqrt{N}$. El Quorum de un nodo está formado por la unión de su fila y su columna en la matriz.

* **Relojes de Lamport:**
    Se utilizan *Timestamps* lógicos para ordenar eventos distribuidos. Esto permite resolver conflictos de prioridad entre solicitudes concurrentes de manera determinista (timestamp más bajo tiene prioridad; en caso de empate, menor ID).

* **Colas de Prioridad (`heapq`):**
    El servidor (`NodeServer`) mantiene una cola de solicitudes pendientes. Si el servidor ya ha otorgado su voto a un nodo A y recibe una petición de un nodo B, no descarta la petición, sino que la encola. Cuando A libera el recurso, el servidor vota automáticamente por el siguiente en la cola.

* **Sincronización:**
    Se emplea `threading.Condition` y `Lock` para manejar los estados de espera (WAITING FOR QUORUM) de forma eficiente, evitando la "espera activa" (busy-waiting) y optimizando el uso de CPU.

### Flujo de Ejecución

1.  **Inicialización:** Los nodos levantan sus servidores y establecen conexiones TCP con sus pares.
2.  **Request:** Un nodo incrementa su reloj, define su timestamp de petición y envía `REQUEST` a su Quorum.
3.  **Wait:** El nodo se bloquea hasta recolectar todos los votos necesarios (`replies`).
4.  **Critical Section:** El nodo trabaja en la SC durante un tiempo simulado.
5.  **Release:** El nodo notifica a su Quorum para que liberen su voto.


## 3. Requisitos y Ejecución

### Requisitos
* **Python 3.x**
* Librerías estándar: `socket`, `threading`, `time`, `random`, `json`, `math`, `heapq`.

### Instrucciones de Ejecución

El sistema se configura mediante el archivo `config.py` y se ejecuta lanzando los nodos.

**1. Configuración (`config.py`)**
Se recomienda utilizar un número de nodos que tenga raíz cuadrada entera (4, 9, 16) para la construcción óptima de la cuadrícula de Maekawa.

```python
numNodes = 4
port = 5000
```

**2. Ejecución**
Para iniciar la simulación hay que ejecutar el programa principal:
```bash
python main.py
```
