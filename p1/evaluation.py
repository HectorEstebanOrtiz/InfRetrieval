import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

class MyEvaluator:
    def __init__(self):
        self.diccionario_relevantes = defaultdict(list)
        self.diccionario_resultados = defaultdict(list)
        self.diccionario_metricas = defaultdict(list)
        self.metricas_total = {
            'precision': 0.0,
            'recall': 0.0,
            'F1': 0.0,
            'prec@10': 0.0,
            'average_precision': 0.0,
            'interpolated_recall_precision': [(0.0, 0.0) for _ in range(11)]
        }

    def sacar_grafica(self):
        if not self.diccionario_metricas:
            print("No hay métricas para graficar. Ejecuta evaluate() primero.")
            return
        x_recall = np.linspace(0.0, 1.0, 11)
        matriz_precisiones = []
        _, ax = plt.subplots()
        for necesidad, metricas in self.diccionario_metricas.items():
            interp_data = metricas.get('interpolated_recall_precision', [])
            # Extraer solo la precisión (y) de cada tupla (recall, precision)
            y_prec = [p for r, p in interp_data]
            matriz_precisiones.append(y_prec)

            ax.plot(x_recall, y_prec, label=f'Information need {necesidad}')

        # Calcular la curva promedio (Eje Y) a lo largo de todas las consultas
        y_promedio = np.mean(matriz_precisiones, axis=0)

        # Graficar la curva promedio global (Sistema)
        ax.plot(x_recall, y_promedio, color='b', linewidth=2.5, label='Total')

        # Configuración del gráfico
        ax.set_title('Curva Precision-Recall Interpolada')
        ax.set_xlabel('Exhaustividad (Recall)')
        ax.set_ylabel('Precision')

        ax.legend(loc='upper right')
        plt.show()

    def Pa10(self,relevantes, resultados):
        top10=resultados[:10]
        true_positives = len(set(top10) & set(relevantes))
        return true_positives/10

    def precisionPromedio(self, relevantes, resultados):
        relevantes_set = set(relevantes)
        
        suma = 0.0
        numRelevantes = 0
        
        for k, doc_id in enumerate(resultados, start=1):
            if doc_id in relevantes_set:
                numRelevantes += 1
                precisionK = numRelevantes / k
                suma += precisionK
                
        # El evaluador exige dividir entre los relevantes encontrados (6 para la Q1),
        # no entre los relevantes totales que existen (8 para la Q1).
        if numRelevantes == 0:
            return 0.0
            
        return suma/numRelevantes

    def recallPrecision(self, relevantes, resultados):
        precisiones = []
        recalls = []
        
        num_rel = len(relevantes)
        if num_rel == 0:
            return precisiones, recalls

        relevantes_set = set(relevantes)
        tp = 0  # Contador de documentos relevantes encontrados

        # Recorremos la lista ordenada de resultados devueltos por el sistema
        for k, doc in enumerate(resultados, start=1):
            if doc in relevantes_set:
                tp += 1
                
                # Calculamos la precisión y el recall en la posición k del acierto
                precision = tp / k
                recall = tp / num_rel

                precisiones.append(precision)
                recalls.append(recall)

        return precisiones, recalls
    
    def precisiones_interpoladas(self, relevantes, resultados):
        # Niveles de recall estándar: [0.0, 0.1, 0.2, ..., 1.0]
        niveles_recall = [r / 10.0 for r in range(11)]
        num_rel = len(relevantes)
        if num_rel == 0:
            return [0.0] * 11, niveles_recall

        relevantes_set = set(relevantes)
        recalls = []
        precisiones = []
        tp = 0

        # 1. Obtenemos las precisiones y recalls no interpolados (al encontrar cada relevante)
        for k, doc in enumerate(resultados, start=1):
            if doc in relevantes_set:
                tp += 1
                precisiones.append(tp / k)
                recalls.append(tp / num_rel)

        # 2. Calculamos la precisión interpolada para cada nivel estándar
        p_interpoladas = []
        for r in niveles_recall:
            # Buscamos todas las precisiones donde el recall obtenido sea >= r
            prec_candidatas = [p for p, rec in zip(precisiones, recalls) if rec >= r]
            
            # Tomamos el máximo valor hallado (si no llegó a ese recall, es 0.0)
            p_interp = max(prec_candidatas) if prec_candidatas else 0.0
            p_interpoladas.append(p_interp)

        return p_interpoladas, niveles_recall

    def evaluate(self, qrels, results, output):
        with open(qrels, 'r') as source:
            for linea in source:
                partes = linea.strip().split()
                necesidad, doc, relevante = partes[0], partes[1], partes[2]
                if relevante == '1':
                    self.diccionario_relevantes[necesidad].append(doc)
        with open(results,'r') as resultados:
            for linea in resultados:
                partes = linea.strip().split()
                necesidad, doc = partes[0], partes[1]
                self.diccionario_resultados[necesidad].append(doc)
        with open(output,'a') as salida:
            i = 0
            for necesidad, docs_relevantes in self.diccionario_relevantes.items():
                docs_recuperados = self.diccionario_resultados.get(necesidad, [])[:45]

                true_positives = len(set(docs_recuperados) & set(docs_relevantes))
                
                # Métricas de Recuperación de Información (evitando división por cero)
                num_relevantes = len(docs_relevantes)
                num_recuperados = len(docs_recuperados)
                precision = true_positives / num_recuperados if num_recuperados > 0 else 0.0
                recall = true_positives / num_relevantes if num_relevantes > 0 else 0.0
                F1 = 2*precision*recall/(precision+recall)
                precA10 = self.Pa10(docs_relevantes, docs_recuperados)
                MAP = self.precisionPromedio(docs_relevantes, docs_recuperados)
                precisiones, recalls = self.recallPrecision(docs_relevantes, docs_recuperados)
                precisiones_inter, recalls_inter = self.precisiones_interpoladas(docs_relevantes, docs_recuperados)
                self.diccionario_metricas[necesidad] = {
                    'precision': precision,
                    'recall': recall,
                    'F1': F1,
                    'prec@10': precA10,
                    'average_precision': MAP,
                    'recall_precision': list(zip(recalls, precisiones)),
                    'interpolated_recall_precision': list(zip(recalls_inter, precisiones_inter))
                }
                
                # Suma directa para los valores simples (escalares)
                self.metricas_total['precision'] += precision
                self.metricas_total['recall'] += recall
                self.metricas_total['prec@10'] += precA10
                self.metricas_total['average_precision'] += MAP

                nuevas_tuplas = []
                for j in range(len(precisiones_inter)):
                    # 1. Sacamos los valores acumulados que ya estaban en el diccionario
                    recall_acumulado = self.metricas_total['interpolated_recall_precision'][j][0]
                    precision_acumulada = self.metricas_total['interpolated_recall_precision'][j][1]
                    
                    # 2. Les sumamos los valores de la consulta actual
                    nuevo_recall = recall_acumulado + recalls_inter[j]
                    nueva_precision = precision_acumulada + precisiones_inter[j]
                    
                    # 3. Guardamos la nueva pareja
                    nuevas_tuplas.append((nuevo_recall, nueva_precision))

                # 4. Reemplazamos la lista antigua del diccionario por la nueva lista sumada
                self.metricas_total['interpolated_recall_precision'] = nuevas_tuplas

                print(f'INFORMATION_NEED {i+1}', file=salida)
                print(f'precision {precision:.3f}', file=salida)
                print(f'recall {recall:.3f}', file=salida)
                print(f'F1 {F1:.3f}', file=salida)
                print(f'prec@10 {precA10:.3f}', file=salida)
                print(f'average_precision {MAP:.3f}', file=salida)
                print(f'recall_precision', file=salida)
                for prec, rec in zip(precisiones, recalls):
                    print(f'{rec:.3f}  {prec:.3f}', file=salida)
                print("interpolated_recall_precision", file=salida)
                for precInt, recInt in zip(precisiones_inter, recalls_inter):
                    print(f'{recInt:.3f}  {precInt:.3f}', file=salida)
                i = i + 1
                
            self.metricas_total['precision'] = self.metricas_total['precision'] / i
            self.metricas_total['recall'] = self.metricas_total['recall'] / i   
            self.metricas_total['F1'] = 2 * self.metricas_total['precision'] * self.metricas_total['recall'] / (self.metricas_total['precision'] + self.metricas_total['recall'])
            self.metricas_total['prec@10'] = self.metricas_total['prec@10'] / i
            self.metricas_total['average_precision'] = self.metricas_total['average_precision'] / i

            medias_interpoladas = []
            # Recorremos la lista de tuplas acumuladas
            for recall_acumulado, precision_acumulada in self.metricas_total['interpolated_recall_precision']:
                # Dividimos ambas partes de la tupla entre i
                recall_medio = recall_acumulado / i
                precision_media = precision_acumulada / i
                
                # Guardamos la nueva tupla ya promediada
                medias_interpoladas.append((recall_medio, precision_media))
            self.metricas_total['interpolated_recall_precision'] = medias_interpoladas

            print(f'TOTAL', file=salida)
            print(f'precision {self.metricas_total["precision"]:.3f}', file=salida)
            print(f'recall {self.metricas_total["recall"]:.3f}', file=salida)
            print(f'F1 {self.metricas_total["F1"]:.3f}', file=salida)
            print(f'prec@10 {self.metricas_total["prec@10"]:.3f}', file=salida)
            print(f'average_precision {self.metricas_total["average_precision"]:.3f}', file=salida)
            print("interpolated_recall_precision", file=salida)
            for recInt, precInt in self.metricas_total["interpolated_recall_precision"]:
                print(f'{recInt:.3f}  {precInt:.3f}', file=salida)
 

if __name__ == '__main__':
    qrels_file = None
    results_file = None
    output_file = None
    i = 1
    while (i < len(sys.argv)):
        if sys.argv[i] == '-qrels':
            qrels_file = sys.argv[i+1]
            i = i + 1
        elif sys.argv[i] == '-results':
            results_file = sys.argv[i+1]
            i = i + 1
        elif sys.argv[i] == '-output':
            output_file = sys.argv[i+1]
            i = i + 1
        i = i + 1
    evaluator = MyEvaluator()
    print(f"qrels: {repr(qrels_file)}, results: {repr(results_file)}, output: {repr(output_file)}")
    evaluator.evaluate(qrels_file,results_file, output_file)
    evaluator.sacar_grafica()