from flask import Flask, render_template, request, jsonify, url_for
import numpy as np
import copy
import os
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

tarimas_data = []

def calcular_makespan(secuencia, tarimas):
    n = len(secuencia)
    m = len(tarimas[0]["T"])
    tiempo_inicio = np.zeros((n, m))
    tiempo_final = np.zeros((n, m))

    for i in range(n):
        idx = secuencia[i] - 1
        for j in range(m):
            if i == 0 and j == 0:
                tiempo_inicio[i][j] = 0
            elif i == 0:
                tiempo_inicio[i][j] = tiempo_final[i][j - 1]
            elif j == 0:
                tiempo_inicio[i][j] = tiempo_final[i - 1][j]
            else:
                tiempo_inicio[i][j] = max(tiempo_final[i - 1][j], tiempo_final[i][j - 1])
            tiempo_final[i][j] = tiempo_inicio[i][j] + tarimas[idx]["T"][j]

    return tiempo_final[-1][-1], tiempo_inicio, tiempo_final

def generar_vecinos(secuencia):
    vecinos = []
    n = len(secuencia)
    for i in range(n):
        for j in range(i + 1, n):
            vecino = copy.deepcopy(secuencia)
            vecino[i], vecino[j] = vecino[j], vecino[i]
            vecinos.append(vecino)
    return vecinos

def algoritmo_neh(tarimas):
    suma_tiempos = [(tarima["id"], np.sum(tarima["T"])) for tarima in tarimas]
    suma_tiempos.sort(key=lambda x: x[1], reverse=True)
    secuencia_ordenada = [item[0] for item in suma_tiempos]

    mejor_secuencia = [secuencia_ordenada[0]]
    mejor_makespan, _, _ = calcular_makespan(mejor_secuencia, tarimas)

    for i in range(1, len(secuencia_ordenada)):
        mejor_makespan_iter = float('inf')
        mejor_secuencia_iter = None

        for j in range(len(mejor_secuencia) + 1):
            nueva_secuencia = mejor_secuencia[:j] + [secuencia_ordenada[i]] + mejor_secuencia[j:]
            makespan, _, _ = calcular_makespan(nueva_secuencia, tarimas)
            if makespan < mejor_makespan_iter:
                mejor_makespan_iter = makespan
                mejor_secuencia_iter = nueva_secuencia

        mejor_secuencia = mejor_secuencia_iter
        mejor_makespan = mejor_makespan_iter

    return mejor_secuencia, mejor_makespan

def busqueda_tabu(tarimas, max_iter=100):
    mejor_secuencia, _ = algoritmo_neh(tarimas)
    mejor_makespan, _, _ = calcular_makespan(mejor_secuencia, tarimas)

    lista_tabu = []
    iteracion = 0

    while iteracion < max_iter:
        vecinos = generar_vecinos(mejor_secuencia)

        mejor_vecino = None
        mejor_makespan_vecino = float('inf')

        for vecino in vecinos:
            if vecino not in lista_tabu:
                makespan_vecino, _, _ = calcular_makespan(vecino, tarimas)
                if makespan_vecino < mejor_makespan_vecino:
                    mejor_vecino = vecino
                    mejor_makespan_vecino = makespan_vecino

        if mejor_vecino is not None:
            mejor_secuencia = mejor_vecino
            mejor_makespan = mejor_makespan_vecino

        lista_tabu.append(mejor_secuencia)
        if len(lista_tabu) > 10:
            lista_tabu.pop(0)

        iteracion += 1

    return mejor_secuencia, mejor_makespan

def graficar_secuencia(secuencia, tiempo_inicio, tiempo_final):
    n = len(secuencia)
    m = len(tiempo_inicio[0])
    colores = plt.cm.tab10.colors

    fig, ax = plt.subplots()

    for i in range(n):
        for j in range(m):
            ax.broken_barh([(tiempo_inicio[i][j], tiempo_final[i][j] - tiempo_inicio[i][j])],
                           (i - 0.4, 0.8), facecolors=colores[j % 10])

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"Tarima {secuencia[i]}" for i in range(n)])
    ax.set_xlabel("Tiempo (minutos)")
    ax.set_title("Flowshop")

    # Guardar la imagen en un archivo
    filename = os.path.join(app.config['STATIC_FOLDER'], 'images', 'grafica.png')
    plt.savefig(filename)
    plt.close()

    return filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cargar_txt', methods=['POST'])
def cargar_txt():
    file = request.files['file']
    if file:
        lines = file.read().decode('utf-8').splitlines()
        tarimas_data.clear()
        for i in range(0, len(lines), 6):
            tiempos = [float(lines[i].strip())]
            tiempos.append(float(lines[i+1].strip()))
            tiempos.append(float(lines[i+2].strip()))
            tiempos.append(float(lines[i+3].strip()))
            tiempos.append(float(lines[i+4].strip()))
            tarimas_data.append({"id": len(tarimas_data) + 1, "T": np.array(tiempos)})
        return jsonify({"message": "Datos cargados exitosamente"})
    return jsonify({"error": "Error al cargar el archivo"}), 400

@app.route('/calcular_secuencia', methods=['POST'])
def calcular_secuencia():
    try:
        data = request.json
        cant_t1 = int(data['cant_t1'])
        cant_t2 = int(data['cant_t2'])
        cant_t3 = int(data['cant_t3'])
        
        secuencia = [1]*cant_t1 + [2]*cant_t2 + [3]*cant_t3
        mejor_secuencia, mejor_makespan = busqueda_tabu([tarimas_data[s-1] for s in secuencia])

        makespan, tiempo_inicio, tiempo_final = calcular_makespan(mejor_secuencia, [tarimas_data[s-1] for s in secuencia])

        # Generar y guardar la gráfica en un archivo
        nombre_grafica = 'grafica.png'
        ruta_grafica = graficar_secuencia(mejor_secuencia, tiempo_inicio, tiempo_final)

        return jsonify({
            "mejor_secuencia": mejor_secuencia,
            "mejor_makespan": mejor_makespan,
            "tiempo_inicio": tiempo_inicio.tolist(),
            "tiempo_final": tiempo_final.tolist(),
            "grafica": url_for('static', filename=f'images/{nombre_grafica}')  # Devolver la ruta de la gráfica generada
        })
    except ValueError:
        return jsonify({"error": "Por favor ingrese números enteros válidos."}), 400

if __name__ == "__main__":
    app.run(debug=True)
