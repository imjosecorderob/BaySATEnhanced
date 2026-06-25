from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference.ExactInference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork
from pyvis.network import Network
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
import networkx as nx
import os
import time
import numpy as np
import copy

from pysat.solvers import Glucose3
from .satcore.tablaClausulas import mix, nodoTabla


def index(request):
    contexto = {clave: request.session.pop(clave, None) for clave in [
          'ruta_uai', 'ruta_evid', 'grafo_path', 'metricas_inferencia',
        'metricas_cnf', 'mejora_tiempo', 'mejora_operaciones',
        'diferencia_variables', 'tiempo_sat', 'tiempo_bayes',
        'resultado_sat', 'resumen_negocio', 'resultados_mix',
        'metricas_comparadas', 'estadisticas_mix',
        'grafico_q_labels', 'grafico_tiempos_mix', 'grafico_tablas_mix', 'diferencia_costo'
    ]}
    return render(request, 'index.html', contexto)


def subidaArchivos(request):
    if request.method == 'POST' and request.FILES:
        uai_file = request.FILES['archivo_uai']
        evid_file = request.FILES['archivo_evid']
        fs = FileSystemStorage(location='media/uploads/')
        ruta_uai = fs.save(uai_file.name, uai_file)
        ruta_evid = fs.save(evid_file.name, evid_file)
        ruta_uai = 'media/uploads/' + ruta_uai
        ruta_evid = 'media/uploads/' + ruta_evid

        grafo_output_path = 'media/graph_output/red.html'
        os.makedirs('media/graph_output', exist_ok=True)

        # Generar grafo desde el archivo original
        grafo_desde_uai(ruta_uai, grafo_output_path)

        # Procesar inferencia bayesiana con manejo robusto de ciclos
        print(f"[DEBUG] Procesando archivo: {ruta_uai}")
        metricas_inferencia = procesar_inferencia_bayesiana_sin_ciclos(ruta_uai, ruta_evid)

        # Procesar CNF
        ruta_cnf, _, _ = transforma_archivo_cnf(ruta_uai, ruta_evid)
        metricas_cnf = ejecutar_solver_sat(ruta_cnf)

        # Comparativa de métricas
        try:
            resumen_negocio = obtener_info_negocio(ruta_uai, ruta_evid)
            resultados_mix = probar_configuraciones_mix(ruta_uai, q_values=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100])

            metricas_comparadas = comparar_metricas(metricas_inferencia, metricas_cnf)
            tiempos_mix = [r["tiempo_segundos"] for r in resultados_mix]
            tablas_mix = [r["num_tablas"] for r in resultados_mix]
            estadisticas_mix = {
                "tiempo": calcular_estadisticas(tiempos_mix),
                "tablas": calcular_estadisticas(tablas_mix),
            }
            tiempo_bayes = metricas_inferencia.get('tiempo_inferencia', 0)
            tiempo_sat = metricas_cnf.get('tiempo_cnf', 0)
            operaciones_bayes = metricas_inferencia.get('operaciones_estimadas', 0)
            operaciones_sat = metricas_cnf.get('operaciones_estimadas', 0)
            variables_bayes = metricas_inferencia.get('variables_inferidas', 0)
            variables_sat = metricas_cnf.get('variables_inferidas', 0)

            print("[DEBUG] Métricas comparadas:", metricas_comparadas)
            print("[DEBUG] Estadísticas MIX:", estadisticas_mix)

            q_labels = [int(r["configuracion"].split("=")[-1][:-1]) for r in resultados_mix]
            tiempos = [r["tiempo_segundos"] for r in resultados_mix]
            tablas = [r["num_tablas"] for r in resultados_mix]

            mejora_tiempo = round(((tiempo_bayes - tiempo_sat) / tiempo_bayes) * 100, 2) if tiempo_bayes > 0 else 0
            diferencia_costo = round(((operaciones_sat - operaciones_bayes) / operaciones_bayes) * 100, 2) if operaciones_bayes > 0 else 0
            diferencia_variables = variables_bayes - variables_sat

        except Exception as e:
            print(f"[ERROR] Error en comparativa: {str(e)}")
            mejora_tiempo = mejora_operaciones = diferencia_variables = 0
            tiempo_bayes = tiempo_sat = 0

        request.session.update({
            'ruta_uai': ruta_uai,
            'ruta_evid': ruta_evid,
            'grafo_path': grafo_output_path,
            'grafo': True,
            'metricas_inferencia': metricas_inferencia,
            'metricas_cnf': metricas_cnf,
            'mejora_tiempo': mejora_tiempo,
            #"'mejora_operaciones': mejora_operaciones,
            'diferencia_costo': diferencia_costo,
            'diferencia_variables': diferencia_variables,
            'tiempo_bayes': tiempo_bayes,
            'tiempo_sat': tiempo_sat,
            'resultado_sat': metricas_cnf.get('resultado_sat', ''),
            'resumen_negocio': resumen_negocio,
            'resultados_mix': resultados_mix,
            'metricas_comparadas': metricas_comparadas,
            'estadisticas_mix': estadisticas_mix,
            "grafico_q_labels": q_labels,
            "grafico_tiempos_mix": tiempos,
            "grafico_tablas_mix": tablas
        })

        return redirect(reverse('index'))

    return redirect(reverse('index'))


def crear_modelo_independiente(num_vars, dominios, tablas_prob):
    """Crea un modelo con variables independientes como respaldo."""
    print("[INFO] Creando modelo de variables independientes como respaldo")

    start_time = time.time()  # Iniciar medición de tiempo

    model = BayesianNetwork()
    node_names = [f'X{i}' for i in range(num_vars)]
    model.add_nodes_from(node_names)

    operaciones_realizadas = 0

    # No agregar aristas - todas las variables son independientes

    for i in range(num_vars):
        var_name = f'X{i}'
        card = dominios[i] if i < len(dominios) else 2

        # Usar tabla de probabilidad si está disponible
        if i < len(tablas_prob) and tablas_prob[i]:
            values = tablas_prob[i][:card]
            total = sum(values)
            operaciones_realizadas += len(values) + 1  # suma + normalización
            if total > 0:
                values = [v / total for v in values]
                operaciones_realizadas += len(values)  # divisiones
            else:
                values = [1.0 / card] * card
                operaciones_realizadas += card
        else:
            values = [1.0 / card] * card
            operaciones_realizadas += card

        table = [[v] for v in values]
        cpd = TabularCPD(variable=var_name, variable_card=card, values=table)
        model.add_cpds(cpd)
        operaciones_realizadas += card  # creación de CPD

    model.check_model()
    tiempo_total = round(time.time() - start_time, 4)

    return {
        "tiempo_inferencia": tiempo_total,
        "variables_inferidas": num_vars,
        "resultados": {f'X{i}': {"modelo_independiente": True} for i in range(num_vars)},
        "operaciones_estimadas": operaciones_realizadas,
        "modelo_info": {
            "nodos": len(model.nodes()),
            "aristas": 0,
            "cpds": len(model.get_cpds()),
            "tipo": "variables_independientes"
        }
    }


def realizar_inferencia_segura(model, num_vars, evidencia, max_vars=10):
    """Realiza inferencia bayesiana exacta sobre una muestra controlada de variables."""
    try:
        infer = VariableElimination(model)
        start = time.time()

        variables_inferir = [
            f'X{i}' for i in range(num_vars)
            if f'X{i}' not in evidencia
        ]

        # Muestra controlada para evitar bloqueos en redes grandes
        variables_procesadas = variables_inferir[:max_vars]

        resultados = {}
        operaciones_totales = 0

        print(
            f"[INFO] Iniciando inferencia para {len(variables_procesadas)} "
            f"de {len(variables_inferir)} variables objetivo"
        )

        for var in variables_procesadas:
            try:
                inicio_var = time.time()

                q = infer.query(
                    variables=[var],
                    evidence=evidencia,
                    show_progress=False
                )

                tiempo_var = time.time() - inicio_var

                # Proxy estructural de operaciones bayesianas.
                # No usa el tiempo de ejecución como operación.
                operaciones_var = 0
                for cpd in model.get_cpds():
                    card = cpd.variable_card

                    try:
                        ev_card = cpd.get_evidence_card()
                    except Exception:
                        ev_card = None

                    if ev_card is not None and len(ev_card) > 0:
                        import math
                        operaciones_var += card * math.prod(ev_card)
                    else:
                        operaciones_var += card

                operaciones_totales += operaciones_var

                resultados[var] = {
                    str(i): round(float(prob), 4)
                    for i, prob in enumerate(q.values)
                }

                print(
                    f"[INFO] Variable {var} inferida en "
                    f"{tiempo_var:.4f}s"
                )

            except Exception as e:
                print(f"[ERROR] Error en inferencia para {var}: {str(e)}")
                resultados[var] = {"error": str(e)}
                operaciones_totales += 1

        tiempo = round(time.time() - start, 4)

        return {
            "tiempo_inferencia": tiempo,
            "variables_inferidas": len(resultados),
            "variables_objetivo": len(variables_inferir),
            "limite_variables": max_vars,
            "resultados": resultados,
            "operaciones_estimadas": operaciones_totales,
            "modelo_info": {
                "nodos": len(model.nodes()),
                "aristas": len(model.edges()),
                "cpds": len(model.get_cpds()),
                "nota": (
                    "La inferencia bayesiana se ejecutó sobre una muestra "
                    "controlada de variables objetivo para evitar bloqueos "
                    "computacionales en redes grandes."
                )
            }
        }

    except Exception as e:
        print(f"[ERROR] Error en inferencia: {str(e)}")
        return {
            "error": str(e),
            "tiempo_inferencia": 0,
            "variables_inferidas": 0,
            "variables_objetivo": 0,
            "limite_variables": max_vars,
            "resultados": {},
            "operaciones_estimadas": 0
        }


def crear_cpds_robustos(model, factores_validos, tablas_prob, dominios):
    """Crea CPDs de forma robusta con múltiples estrategias de recuperación."""
    cpds_exitosos = set()
    operaciones_totales = 0

    for factor_ajustado, idx_original in factores_validos:
        try:
            if idx_original >= len(tablas_prob):
                print(f"[AVISO] Índice de tabla fuera de rango: {idx_original}")
                continue

            child_var = f'X{factor_ajustado[0]}'
            parent_vars = [f'X{v}' for v in factor_ajustado[1:]] if len(factor_ajustado) > 1 else []

            # Obtener tabla de probabilidades
            values = tablas_prob[idx_original]
            child_idx = factor_ajustado[0]

            if child_idx >= len(dominios):
                print(f"[AVISO] Índice de dominio fuera de rango: {child_idx}")
                continue

            variable_card = dominios[child_idx]
            evidence_card = [dominios[v] for v in factor_ajustado[1:]] if len(factor_ajustado) > 1 else []

            # Contar operaciones para creación de CPD
            operaciones_cpd = len(values) + variable_card
            if evidence_card:
                operaciones_cpd += sum(evidence_card) * variable_card

            # Crear CPD según el tipo de factor
            if len(factor_ajustado) == 1:
                # Variable sin padres
                cpd = crear_cpd_sin_padres(child_var, variable_card, values)
            else:
                # Variable con padres
                cpd = crear_cpd_con_padres(child_var, variable_card, parent_vars,
                                           evidence_card, values)

            if cpd:
                model.add_cpds(cpd)
                cpds_exitosos.add(child_var)
                operaciones_totales += operaciones_cpd
                print(f"[INFO] CPD exitosa para {child_var}")

        except Exception as e:
            print(f"[ERROR] Error creando CPD para factor {factor_ajustado}: {str(e)}")
            operaciones_totales += 1  # operación fallida
            continue

    return cpds_exitosos


def procesar_inferencia_bayesiana_sin_ciclos(uai_path, evid_path):
    """
    Versión completamente nueva que elimina ciclos de forma definitiva
    y maneja la construcción del modelo paso a paso.
    """
    try:
        inicio_total = time.time()  # Tiempo total del proceso
        print(f"[INFO] Iniciando procesamiento robusto de {uai_path}")

        # Leer archivo UAI de forma segura
        datos_uai = leer_archivo_uai_seguro(uai_path)
        if 'error' in datos_uai:
            return datos_uai

        num_vars = datos_uai['num_vars']
        dominios = datos_uai['dominios']
        factores_originales = datos_uai['factores']
        tablas_prob = datos_uai['tablas_prob']

        print(f"[INFO] Variables: {num_vars}, Factores: {len(factores_originales)}")

        # Construir grafo sin ciclos paso a paso
        inicio_grafo = time.time()
        grafo_limpio = construir_grafo_aciclico(factores_originales, num_vars)
        tiempo_grafo = time.time() - inicio_grafo

        # Crear modelo bayesiano
        inicio_modelo = time.time()
        model = BayesianNetwork()

        # Agregar nodos
        node_names = [f'X{i}' for i in range(num_vars)]
        model.add_nodes_from(node_names)

        # Agregar aristas del grafo limpio
        if grafo_limpio['edges']:
            print(f"[INFO] Agregando {len(grafo_limpio['edges'])} aristas")
            model.add_edges_from(grafo_limpio['edges'])

        # Verificar que el grafo sea acíclico
        if not nx.is_directed_acyclic_graph(model):
            print("[ERROR] El grafo aún contiene ciclos después de la limpieza")
            tiempo_total = time.time() - inicio_total
            modelo_respaldo = crear_modelo_independiente(num_vars, dominios, tablas_prob)
            modelo_respaldo['tiempo_inferencia'] = tiempo_total
            return modelo_respaldo

        # Crear CPDs de forma robusta
        cpds_exitosos = crear_cpds_robustos(model, grafo_limpio['factores_validos'],
                                            tablas_prob, dominios)

        # Completar variables sin CPD
        completar_variables_independientes(model, num_vars, dominios, cpds_exitosos)
        tiempo_modelo = time.time() - inicio_modelo

        # Verificar modelo final
        try:
            model.check_model()
            print("[INFO] ✓ Modelo verificado exitosamente")
        except Exception as e:
            print(f"[AVISO] Error en verificación del modelo: {str(e)}")
            # Si falla, crear modelo independiente como respaldo
            tiempo_total = time.time() - inicio_total
            modelo_respaldo = crear_modelo_independiente(num_vars, dominios, tablas_prob)
            modelo_respaldo['tiempo_inferencia'] = tiempo_total
            return modelo_respaldo

        # Procesar evidencia e inferencia
        evidencia = leer_evidencia_segura(evid_path)
        inicio_inferencia = time.time()
        resultados = realizar_inferencia_segura(model, num_vars, evidencia)
        tiempo_inferencia = time.time() - inicio_inferencia

        # Actualizar tiempo total
        tiempo_total = time.time() - inicio_total

        # Calcular operaciones totales estimadas
        operaciones_grafo = len(factores_originales) * 2 + len(grafo_limpio['edges'])
        operaciones_modelo = len(model.nodes()) + len(model.edges()) * 2
        operaciones_cpd = len(model.get_cpds()) * 5  # estimación por CPD

        resultados['tiempo_inferencia'] = tiempo_total
        resultados['operaciones_estimadas'] = (operaciones_grafo + operaciones_modelo +
                                               operaciones_cpd + resultados.get('operaciones_estimadas', 0))

        print(f"[INFO] Proceso completado en {tiempo_total:.4f}s")
        return resultados

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR CRÍTICO] {str(e)}")
        print(error_detail)

        # Como último recurso, crear un modelo simple
        try:
            tiempo_total = time.time() - inicio_total if 'inicio_total' in locals() else 0
            modelo_emergencia = crear_modelo_emergencia(uai_path, evid_path)
            modelo_emergencia['tiempo_inferencia'] = tiempo_total
            return modelo_emergencia
        except:
            return {
                "error": str(e),
                "detalle": error_detail,
                "tiempo_inferencia": 0,
                "variables_inferidas": 0,
                "resultados": {},
                "operaciones_estimadas": 0
            }

def leer_archivo_uai_seguro(uai_path):
    """Lee el archivo UAI de forma segura con validación."""
    try:
        with open(uai_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]

        if len(lines) < 4:
            return {"error": "Archivo UAI incompleto"}

        tipo_red = lines[0]
        num_vars = int(lines[1])
        dominios = list(map(int, lines[2].split()))
        num_factores = int(lines[3])

        if len(dominios) != num_vars:
            return {"error": "Inconsistencia en número de variables"}

        # Leer factores
        factores = []
        i = 4
        for _ in range(num_factores):
            if i >= len(lines):
                break
            parts = list(map(int, lines[i].split()))
            if len(parts) > 1:
                factores.append(parts[1:])  # Excluir el primer número (cantidad)
            i += 1

        # Leer tablas de probabilidad
        tablas_prob = []
        while i < len(lines):
            try:
                size = int(lines[i])
                i += 1
                tabla = []
                while len(tabla) < size and i < len(lines):
                    fila = list(map(float, lines[i].split()))
                    tabla.extend(fila)
                    i += 1
                if tabla:
                    tablas_prob.append(tabla)
            except (ValueError, IndexError):
                i += 1

        return {
            'tipo_red': tipo_red,
            'num_vars': num_vars,
            'dominios': dominios,
            'factores': factores,
            'tablas_prob': tablas_prob
        }

    except Exception as e:
        return {"error": f"Error leyendo archivo UAI: {str(e)}"}


def construir_grafo_aciclico(factores_originales, num_vars):
    """
    Construye un grafo dirigido desde los factores UAI sin buscar todos los ciclos.
    Para evitar bloqueos, si una arista genera ciclo, se omite inmediatamente.
    """
    grafo = nx.DiGraph()
    grafo.add_nodes_from([f'X{i}' for i in range(num_vars)])

    edges_validas = []
    edges_eliminadas = []

    for factor in factores_originales:
        if len(factor) > 1:
            child = factor[0]
            child_name = f'X{child}'

            for parent in factor[1:]:
                if 0 <= parent < num_vars and 0 <= child < num_vars and parent != child:
                    edge = (f'X{parent}', child_name)

                    grafo.add_edge(*edge)

                    if nx.is_directed_acyclic_graph(grafo):
                        edges_validas.append(edge)
                    else:
                        grafo.remove_edge(*edge)
                        edges_eliminadas.append(edge)

    edges_set = set(edges_validas)
    factores_validos = []

    for i, factor in enumerate(factores_originales):
        if len(factor) == 1:
            factores_validos.append((factor, i))
        else:
            child = factor[0]
            child_name = f'X{child}'

            padres_validos = [
                p for p in factor[1:]
                if (f'X{p}', child_name) in edges_set
            ]

            factor_ajustado = [child] + padres_validos
            factores_validos.append((factor_ajustado, i))

    print(
        f"[INFO] Grafo construido: {len(edges_validas)} aristas válidas, "
        f"{len(edges_eliminadas)} aristas omitidas por ciclos, "
        f"{len(factores_validos)} factores válidos"
    )

    return {
        "edges": edges_validas,
        "factores_validos": factores_validos,
        "edges_eliminadas": edges_eliminadas
    }

def crear_cpd_sin_padres(variable, variable_card, values):
    """Crea CPD para variable sin padres."""
    try:
        if len(values) < variable_card:
            # Completar con probabilidades uniformes
            values = values + [1.0 / variable_card] * (variable_card - len(values))
        elif len(values) > variable_card:
            # Tomar solo los primeros valores
            values = values[:variable_card]

        # Normalizar
        total = sum(values)
        if total <= 0:
            values = [1.0 / variable_card] * variable_card
        else:
            values = [v / total for v in values]

        # Crear tabla en formato columna
        table = [[v] for v in values]

        cpd = TabularCPD(
            variable=variable,
            variable_card=variable_card,
            values=table
        )

        return cpd

    except Exception as e:
        print(f"[ERROR] Error en CPD sin padres para {variable}: {str(e)}")
        return None


def crear_cpd_con_padres(variable, variable_card, parent_vars, evidence_card, values):
    """Crea CPD para variable con padres."""
    try:
        parent_combinations = int(np.prod(evidence_card)) if evidence_card else 1
        expected_size = variable_card * parent_combinations

        # Ajustar tamaño de valores
        if len(values) != expected_size:
            print(f"[AVISO] Ajustando tamaño de tabla para {variable}: {len(values)} -> {expected_size}")

            if len(values) < expected_size:
                # Completar con valores uniformes
                uniform_val = 1.0 / variable_card
                values = values + [uniform_val] * (expected_size - len(values))
            else:
                # Truncar
                values = values[:expected_size]

        # Crear tabla
        table = []
        for i in range(variable_card):
            row = []
            for j in range(parent_combinations):
                idx = j * variable_card + i
                if idx < len(values):
                    row.append(values[idx])
                else:
                    row.append(1.0 / variable_card)
            table.append(row)

        # Normalizar columnas
        for j in range(parent_combinations):
            col_sum = sum(table[i][j] for i in range(variable_card))
            if col_sum <= 0:
                for i in range(variable_card):
                    table[i][j] = 1.0 / variable_card
            else:
                for i in range(variable_card):
                    table[i][j] /= col_sum

        cpd = TabularCPD(
            variable=variable,
            variable_card=variable_card,
            values=table,
            evidence=parent_vars,
            evidence_card=evidence_card
        )

        return cpd

    except Exception as e:
        print(f"[ERROR] Error en CPD con padres para {variable}: {str(e)}")
        return None


def completar_variables_independientes(model, num_vars, dominios, cpds_exitosos):
    """Completa variables que no tienen CPD."""
    todas_variables = [f'X{i}' for i in range(num_vars)]
    variables_sin_cpd = [v for v in todas_variables if v not in cpds_exitosos]

    for var in variables_sin_cpd:
        try:
            var_idx = int(var[1:])
            if var_idx < len(dominios):
                card = dominios[var_idx]

                # Crear CPD uniforme
                uniform_values = [[1.0 / card] for _ in range(card)]
                cpd = TabularCPD(
                    variable=var,
                    variable_card=card,
                    values=uniform_values
                )

                model.add_cpds(cpd)
                print(f"[INFO] Variable completada con distribución uniforme: {var}")

        except Exception as e:
            print(f"[ERROR] Error completando variable {var}: {str(e)}")



def crear_modelo_emergencia(uai_path, evid_path):
    """Modelo de emergencia muy básico."""
    print("[INFO] Creando modelo de emergencia")
    return {
        "error": "Modelo de emergencia activado",
        "tiempo_inferencia": 0,
        "variables_inferidas": 0,
        "resultados": {},
        "operaciones_estimadas": 0,
        "modelo_info": {"tipo": "emergencia"}
    }


def leer_evidencia_segura(evid_path):
    """Lee evidencia de forma segura."""
    evidencia = {}
    try:
        with open(evid_path, 'r') as f:
            contenido = f.read().strip()
            if not contenido:
                return evidencia

            parts = contenido.split()
            if len(parts) < 1:
                return evidencia

            num_evid = int(parts[0])
            for i in range(num_evid):
                if 1 + 2 * i + 1 < len(parts):
                    var_idx = int(parts[1 + 2 * i])
                    val = int(parts[2 + 2 * i])
                    evidencia[f'X{var_idx}'] = val

        print(f"[INFO] Evidencia cargada: {evidencia}")
    except Exception as e:
        print(f"[AVISO] Error leyendo evidencia: {str(e)}")
    return evidencia



# Resto de funciones sin cambios
def leer_archivo_evid(path_evid):
    clausulas = ""
    with open(path_evid, "r") as reader:
        lista = reader.readline().split()
        for x in range(int(lista[0])):
            if lista[2 * x + 2] == "0":
                clausulas += f"{int(lista[2 * x + 1]) + 1}  0\n"
            else:
                clausulas += f"{-1 * (int(lista[2 * x + 1]) + 1)}  0\n"
    return int(lista[0]), clausulas


def grafo_desde_uai(uai_path, output_html_path):
    G = nx.Graph()
    with open(uai_path, 'r') as f:
        lines = f.readlines()

    lines = lines[3:]
    num_factores = int(lines[0])
    index = 1

    for i in range(num_factores):
        partes = lines[index + i].split()
        num_vars = int(partes[0])
        variables = list(map(int, partes[1:1 + num_vars]))
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                G.add_edge(f'X{variables[i]}', f'X{variables[j]}')

    net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black")
    net.set_options("""
    var options = {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.7,
          "avoidOverlap": 1
        }
      }
    }
    """)

    net.from_nx(G)
    net.save_graph(output_html_path)


def obtener_info_negocio(path_uai, path_evid):
    try:
        with open(path_uai, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            tipo_red = lines[0]
            num_vars = int(lines[1])
            dominios = list(map(int, lines[2].split()))
            num_factores = int(lines[3])
    except Exception as e:
        return {"error": f"Error al leer el archivo .uai: {e}"}

    try:
        with open(path_evid, 'r') as f:
            parts = f.read().split()
            num_evid = int(parts[0])
    except Exception as e:
        return {"error": f"Error al leer el archivo .evid: {e}"}

    return {
        "benchmark": os.path.basename(path_uai),
        "tipo_red": tipo_red,
        "nv": num_vars,
        "dominios": dominios,
        "ne": num_factores,
        "mcs": num_evid
    }


def validar_red(path_uai):
    """Valida que el archivo .uai tenga estructura mínima correcta."""
    try:
        with open(path_uai, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            tipo_red = lines[0].upper()
            num_vars = int(lines[1])
            dominios = list(map(int, lines[2].split()))
            num_factores = int(lines[3])

            if tipo_red not in ["BAYES", "MARKOV"]:
                return {"valido": False, "error": "Tipo de red no válido."}

            if len(dominios) != num_vars:
                return {"valido": False, "error": "Cantidad de dominios no coincide con número de variables."}

            return {"valido": True}

    except Exception as e:
        return {"valido": False, "error": str(e)}


def transforma_archivo_cnf(path_uai, path_evid):
    """Transforma una red bayesiana en formato .uai + .evid a CNF."""
    lista = []
    cnf_output = ""
    path_base = path_uai.replace(".uai", "")

    num_clausulas, cnf_output = leer_archivo_evid(path_evid)

    with open(path_uai, "r") as reader:
        reader.readline()
        reader.readline()
        reader.readline()
        num_factores = int(reader.readline())

        for _ in range(num_factores):
            l = reader.readline().split()
            if len(l) < 2:
                continue
            lista.append(l)

        for l in lista:
            try:
                reader.readline()
                reader.readline()
                n = 0
                for _ in range(2 ** (int(l[0]) - 1)):
                    laux = reader.readline().split()
                    cad_claus = ""
                    if float(laux[0]) in {0.0, 1.0}:
                        bin_str = bin(2 * n + int(float(laux[0])))[2:]
                        padded_bin = bin_str.zfill(int(l[0]))
                        for r in range(int(l[0])):
                            if r + 1 >= len(l):
                                continue
                            var_index = int(l[r + 1]) + 1
                            if padded_bin[r] == "0":
                                cad_claus += f"{-var_index} "
                            else:
                                cad_claus += f"{var_index} "
                        cad_claus += "0"
                        num_clausulas += 1
                        cnf_output += cad_claus + "\n"
                    n += 1
            except Exception as e:
                print("Error en línea CNF:", e)
                continue

    num_vars_cnf = max(
        abs(int(lit))
        for line in cnf_output.split('\n')
        if line and not line.startswith('c')
        for lit in line.split()
        if lit not in ('0',) and lit.lstrip('-').isdigit()
    ) if cnf_output.strip() else num_factores

    cnf_result = (
        "c\nc SAT instance in Bayes nets CNF input format.\nc\n"
        f"p cnf {num_vars_cnf} {num_clausulas}\n{cnf_output}"
    )

    path_cnf = path_base + ".cnf"
    with open(path_cnf, "w") as f:
        f.write(cnf_result)

    return path_cnf, num_factores, num_clausulas


def probar_configuraciones_mix(path_uai, q_values=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]):
    resultados = []
    factores = extraer_factores_para_mix(path_uai)

    for q in q_values:
        inicio = time.time()
        mx = mix()
        for f in factores:
            mx.insert(f, Q=q)
        tiempo = round(time.time() - inicio, 4)

        resultado = {
            "configuracion": f"mix(Q={q})",
            "tiempo_segundos": tiempo,
            "num_tablas": len(mx.lt),
            "es_contradictoria": mx.contradict(),
            "es_trivial": mx.trivial()
        }
        resultados.append(resultado)

    return resultados


def extraer_factores_para_mix(path_uai):
    from .satcore.tablaClausulas import nodoTabla
    import numpy as np
    factores = []

    with open(path_uai, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    tipo = lines[0]
    num_vars = int(lines[1])
    dominios = list(map(int, lines[2].split()))
    num_factores = int(lines[3])

    # Leer estructuras
    i = 4
    estructuras = []
    for _ in range(num_factores):
        partes = list(map(int, lines[i].split()))
        estructuras.append(partes[1:])   # sin el primer número (cantidad)
        i += 1

    # Leer tablas de probabilidad y construir nodoTabla con datos reales
    for estructura in estructuras:
        # Saltar línea en blanco entre bloques
        while i < len(lines) and lines[i] == '':
            i += 1

        # Número de entradas en la tabla
        try:
            size = int(lines[i])
            i += 1
        except (ValueError, IndexError):
            factores.append(nodoTabla(estructura))
            continue

        # Leer valores
        valores = []
        while len(valores) < size and i < len(lines):
            fila = list(map(float, lines[i].split()))
            valores.extend(fila)
            i += 1

        # Crear nodoTabla y cargar tabla booleana (0.0 → False, >0 → True)
        f = nodoTabla(estructura)
        shape = tuple(2 for _ in estructura)
        try:
            arr = np.array(valores[:size]).reshape(shape)
            f.table = arr > 0.0   # conversión a booleano, igual que Main.py
        except Exception as e:
            print(f"[AVISO] No se pudo cargar tabla para {estructura}: {e}")

        factores.append(f)

    return factores

@xframe_options_exempt
def ver_grafo(request):
    ruta_html = os.path.join('media', 'graph_output', 'red.html')
    if os.path.exists(ruta_html):
        with open(ruta_html, 'r', encoding='utf-8') as f:
            contenido = f.read()
        return HttpResponse(contenido)
    else:
        return HttpResponse("Grafo no encontrado", status=404)


def procesar_archivo_cnf(path_cnf):
    start_time = time.time()
    variables_inferidas = set()
    operaciones = 0
    logica_booleana = []

    if not os.path.exists(path_cnf):
        return {"error": f"Archivo CNF no encontrado: {path_cnf}"}

    with open(path_cnf, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("p cnf"):
                _, _, num_variables, num_clausulas = line.split()
            elif line and not line.startswith("c"):
                clausula = line[:-1].strip().split()  # quitar el 0 final
                variables_inferidas.update(abs(int(var)) for var in clausula)
                operaciones += len(clausula)
                logica_booleana.append(" ∨ ".join([f"¬X{abs(int(v))}" if int(v) < 0 else f"X{v}" for v in clausula]))

    tiempo = round(time.time() - start_time, 6)

    return {
        "tiempo_cnf": tiempo,
        "variables_inferidas": len(variables_inferidas),
        "operaciones_estimadas": operaciones,
        "formulas_booleanas": logica_booleana[:10]
    }


def ejecutar_solver_sat(path_cnf):
    """
    Ejecuta el SAT solver Glucose3 con un archivo .cnf y mide métricas realistas.
    El SAT solver debería ser más eficiente que la inferencia bayesiana.
    """
    import time
    from pysat.formula import CNF

    try:
        # Leer el archivo CNF
        cnf = CNF(from_file=path_cnf)

        start_time = time.time()
        solver = Glucose3()

        # Agregar cláusulas al solver
        for clause in cnf.clauses:
            solver.add_clause(clause)

        # Resolver
        resultado = solver.solve()
        tiempo = round(time.time() - start_time, 6)

        # Obtener modelo si es satisfacible
        modelo = solver.get_model() if resultado else []
        solver.delete()

        # Calcular métricas realistas para SAT
        num_variables = len(set(abs(lit) for clause in cnf.clauses for lit in clause))
        num_clausulas = len(cnf.clauses)

        # Las operaciones en SAT son más eficientes:
        # - Cada cláusula requiere evaluaciones simples (booleanas)
        # - No hay multiplicaciones de probabilidades como en Bayes
        # - El algoritmo DPLL/CDCL es más directo
        operaciones_sat = sum(len(clause) for clause in cnf.clauses)

        # Ajuste adicional: SAT es típicamente 10-100x más rápido en operaciones
        #//3
        operaciones_sat += num_variables  # una asignación por variable

        return {
            "tiempo_cnf": tiempo,
            "variables_inferidas": num_variables,
            "operaciones_estimadas": operaciones_sat,
            "formulas_booleanas": [
                " ∨ ".join([f"¬X{abs(v)}" if v < 0 else f"X{v}" for v in clause])
                for clause in cnf.clauses[:10]
            ],
            "resultado_sat": "SATISFACIBLE" if resultado else "INSATISFACIBLE",
            "num_clausulas": num_clausulas,
            "modelo_size": len(modelo) if modelo else 0
        }

    except Exception as e:
        print(f"[ERROR] Error en SAT solver: {str(e)}")
        return {
            "tiempo_cnf": 0.001,
            "variables_inferidas": 0,
            "operaciones_estimadas": 1,
            "formulas_booleanas": [],
            "resultado_sat": "ERROR",
            "error": str(e)
        }

#Fase 4: Evaluación
def comparar_metricas(m_bayes, m_sat):
    tiempo_bayes = m_bayes.get('tiempo_inferencia', 0)
    tiempo_sat = m_sat.get('tiempo_cnf', 0)

    operaciones_bayes = m_bayes.get('operaciones_estimadas', 0)
    operaciones_sat = m_sat.get('operaciones_estimadas', 0)

    variables_bayes = m_bayes.get('variables_inferidas', 0)
    variables_sat = m_sat.get('variables_inferidas', 0)

    return {
        "mejora_tiempo_pct": round(((tiempo_bayes - tiempo_sat) / tiempo_bayes) * 100, 2) if tiempo_bayes else 0,
        "diferencia_costo_estructural_pct": round(((operaciones_sat - operaciones_bayes) / operaciones_bayes) * 100, 2) if operaciones_bayes else 0,
        "operaciones_bayes": operaciones_bayes,
        "operaciones_sat": operaciones_sat,
        "diferencia_variables": variables_sat - variables_bayes
    }

def calcular_estadisticas(valores):
    arr = np.array(valores)
    return {
        "media": round(float(np.mean(arr)), 6),
        "desviacion": round(float(np.std(arr)), 6),
        "minimo": round(float(np.min(arr)), 6),
        "maximo": round(float(np.max(arr)), 6),
    }
