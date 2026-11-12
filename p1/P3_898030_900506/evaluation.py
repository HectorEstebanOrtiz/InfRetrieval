import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
#Autores: Ciro Fustero Zumeta (NIP: 900506) y Héctor Esteban Ortiz (NIP: 898030)

class MyEvaluator:
    def __init__(self):
        self.diccionario_relevantes = defaultdict(list) #diccionario que contiene las necesidades de información y los documentos relevantes asociados a cada una
        self.diccionario_resultados = defaultdict(list) #diccionario que contiene las necesidades de información y los documentos recuperados por el sistema asociados a cada una
        self.diccionario_metricas = defaultdict(list) #diccionario que contiene las necesidades de información y las métricas de evaluación asociadas a cada una
        self.metricas_total = {
            'precision': 0.0,
            'recall': 0.0,
            'F1': 0.0,
            'prec@10': 0.0,
            'average_precision': 0.0,
            'interpolated_recall_precision': [(0.0, 0.0) for _ in range(11)]
        } #diccionario que contiene las métricas de evaluación globales del sistema, calculadas como la media de las métricas de cada necesidad de información (excepto la F1, que se calcula a partir de la media de precision y recall)

    #Metodo que muestra la gráfica precision/recall de los puntos tomados
    def sacar_grafica(self):
        if not self.diccionario_metricas:
            print("No hay métricas para graficar. Ejecuta evaluate() primero.")
            return
        x_recall = np.linspace(0.0, 1.0, 11)
        matriz_precisiones = []
        _, ax = plt.subplots()
        for necesidad, metricas in self.diccionario_metricas.items():
            interp_data = metricas.get('interpolated_recall_precision', [])
            #extraer solo la precisión de cada elemento del diccionario (recall, precision)
            y_prec = [p for r, p in interp_data]
            matriz_precisiones.append(y_prec)

            ax.plot(x_recall, y_prec, label=f'Information need {necesidad}')

        #calcular la curva promedio (Eje Y) a lo largo de todas las consultas
        y_promedio = np.mean(matriz_precisiones, axis=0)

        #graficar la curva promedio global (Sistema)
        ax.plot(x_recall, y_promedio, color='b', linewidth=2.5, label='Total')

        #configuración del gráfico
        ax.set_title('Curva Precision-Recall Interpolada')
        ax.set_xlabel('Exhaustividad (Recall)')
        ax.set_ylabel('Precision')

        ax.legend(loc='upper right')
        plt.show()

    #Metodo que calcula prec@10
    def Pa10(self,relevantes, resultados): #calcula la precision de los 10 primeros resultados devueltos por el sistema
        top10=resultados[:10]
        true_positives = len(set(top10) & set(relevantes))
        return true_positives/10

    #Metodo que calcula el MAP
    def precisionPromedio(self, relevantes, resultados): #calcula la precision promedio de los resultados devueltos por el sistema
        relevantes_set = set(relevantes)
        
        suma = 0.0
        numRelevantes = 0
        
        for k, doc_id in enumerate(resultados, start=1):
            if doc_id in relevantes_set: #cada vez que se devuelve un documento relevante, se calcula la precision en ese punto y se suma a la suma total
                numRelevantes += 1 
                suma += numRelevantes / k
                
        #el evaluador exige dividir entre los relevantes encontrados, en caso de que no haya ninguno, devolver 0.0
        if numRelevantes == 0:
            return 0.0
            
        return suma/numRelevantes #para sacar la precision promedio, se divide la suma de las precisiones en cada punto relevante entre el numero de relevantes encontrados

    #Metodo que calcula la precision y recall cada vez que aparece un documento relevante
    def recallPrecision(self, relevantes, resultados):
        precisiones = []
        recalls = []
        
        num_rel = len(relevantes) #si no hay ningún documento relevante, no se puede calcular la precision ni el recall, por lo que se devuelve una lista vacía
        if num_rel == 0:
            return precisiones, recalls

        relevantes_set = set(relevantes)
        tp = 0  #contador de documentos relevantes encontrados

        #recorremos la lista ordenada de resultados devueltos por el sistema
        for k, doc in enumerate(resultados, start=1):
            if doc in relevantes_set:
                tp += 1
                
                #calculamos la precisión y el recall en la posición k del acierto
                precision = tp / k
                recall = tp / num_rel

                precisiones.append(precision)
                recalls.append(recall)

        return precisiones, recalls
    
    #Metodo que calcula la precision y recall en 11 puntos
    def precisiones_interpoladas(self, relevantes, resultados):
        #niveles de recall estándar: [0.0, 0.1, 0.2, ..., 1.0]
        niveles_recall = [r / 10.0 for r in range(11)]
        num_rel = len(relevantes)
        if num_rel == 0:
            return [0.0] * 11, niveles_recall #si no hay relevantes se devuelve una lista de 11 ceros

        relevantes_set = set(relevantes)
        recalls = []
        precisiones = []
        tp = 0

        #obtenemos las precisiones y recalls no interpolados (al encontrar cada relevante)
        for k, doc in enumerate(resultados, start=1):
            if doc in relevantes_set:
                tp += 1
                precisiones.append(tp / k)
                recalls.append(tp / num_rel)

        #calculamos la precisión interpolada para cada nivel estándar
        p_interpoladas = []
        for r in niveles_recall:
            #buscamos todas las precisiones donde el recall obtenido sea >= r
            prec_candidatas = [p for p, rec in zip(precisiones, recalls) if rec >= r]
            
            #tomamos el máximo valor hallado o 0.0 si no hay ninguno que llegue ahí
            p_interp = max(prec_candidatas) if prec_candidatas else 0.0
            p_interpoladas.append(p_interp)

        return p_interpoladas, niveles_recall

    #Metodo que calcula, guarda e imprime en "output"/pantalla las metricas pedidas en la practica
    def evaluate(self, qrels, results, output):
        #Abrimos el fichero que dicta la relevancia de los documentos
        with open(qrels, 'r') as source:
            for linea in source:
                partes = linea.strip().split()
                necesidad, doc, relevante = partes[0], partes[1], partes[2]
                if relevante == '1':
                    self.diccionario_relevantes[necesidad].append(doc)
        #Abrimos el fichero de los resultados del sistema de informacion
        with open(results,'r') as resultados:
            for linea in resultados:
                partes = linea.strip().split()
                necesidad, doc = partes[0], partes[1]
                self.diccionario_resultados[necesidad].append(doc)
        #Escribimos las metricas
        with open(output,'a') as salida:
            i = 0
            for necesidad, docs_relevantes in self.diccionario_relevantes.items():
                docs_recuperados = self.diccionario_resultados.get(necesidad, [])[:45]

                true_positives = len(set(docs_recuperados) & set(docs_relevantes))
                
                #Calculamos las metricas pedidas
                num_relevantes = len(docs_relevantes)
                num_recuperados = len(docs_recuperados)
                precision = true_positives / num_recuperados if num_recuperados > 0 else 0.0
                recall = true_positives / num_relevantes if num_relevantes > 0 else 0.0
                F1 = 2*precision*recall/(precision+recall)
                precA10 = self.Pa10(docs_relevantes, docs_recuperados)
                MAP = self.precisionPromedio(docs_relevantes, docs_recuperados)
                precisiones, recalls = self.recallPrecision(docs_relevantes, docs_recuperados)
                precisiones_inter, recalls_inter = self.precisiones_interpoladas(docs_relevantes, docs_recuperados)
                
                #Guardamos en un diccionario las métricas para no tener que volver a calcularlas
                self.diccionario_metricas[necesidad] = {
                    'precision': precision,
                    'recall': recall,
                    'F1': F1,
                    'prec@10': precA10,
                    'average_precision': MAP,
                    'recall_precision': list(zip(recalls, precisiones)),
                    'interpolated_recall_precision': list(zip(recalls_inter, precisiones_inter))
                }
                
                #Acumulamos las metricas para despues calcular el total
                self.metricas_total['precision'] += precision
                self.metricas_total['recall'] += recall
                self.metricas_total['prec@10'] += precA10
                self.metricas_total['average_precision'] += MAP

                nuevas_tuplas = []
                #Calculamos la acumulacion de precisiones y recalls
                for j in range(len(precisiones_inter)):
                    #Sacamos los valores acumulados que ya estaban en el diccionario
                    recall_acumulado = self.metricas_total['interpolated_recall_precision'][j][0]
                    precision_acumulada = self.metricas_total['interpolated_recall_precision'][j][1]
                    #Les sumamos los valores de la consulta actual
                    nuevo_recall = recall_acumulado + recalls_inter[j]
                    nueva_precision = precision_acumulada + precisiones_inter[j]
                    #Guardamos la nueva pareja
                    nuevas_tuplas.append((nuevo_recall, nueva_precision))
                #Reemplazamos la lista antigua del diccionario por la nueva lista sumada
                self.metricas_total['interpolated_recall_precision'] = nuevas_tuplas

                #Imprimimos las métricas de la necesidad
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
                print("", file=salida)
                i = i + 1

            #Dividimos todas las métricas entre i (numero de necesidades) para sacar las medias (total)
            self.metricas_total['precision'] = self.metricas_total['precision'] / i
            self.metricas_total['recall'] = self.metricas_total['recall'] / i   
            self.metricas_total['F1'] = 2 * self.metricas_total['precision'] * self.metricas_total['recall'] / (self.metricas_total['precision'] + self.metricas_total['recall'])
            self.metricas_total['prec@10'] = self.metricas_total['prec@10'] / i
            self.metricas_total['average_precision'] = self.metricas_total['average_precision'] / i

            medias_interpoladas = []
            #Recorremos los recalls y precisiones acumuladsa
            for recall_acumulado, precision_acumulada in self.metricas_total['interpolated_recall_precision']:
                #Dividimos ambas partes de la tupla entre i para sacar el promedi
                recall_medio = recall_acumulado / i
                precision_media = precision_acumulada / i
                #Guardamos la nueva tupla ya promediada
                medias_interpoladas.append((recall_medio, precision_media))
            #Actualizamos el valor en la lista
            self.metricas_total['interpolated_recall_precision'] = medias_interpoladas

            #Imprimimos los resultados totales
            print(f'TOTAL', file=salida)
            print(f'precision {self.metricas_total["precision"]:.3f}', file=salida)
            print(f'recall {self.metricas_total["recall"]:.3f}', file=salida)
            print(f'F1 {self.metricas_total["F1"]:.3f}', file=salida)
            print(f'prec@10 {self.metricas_total["prec@10"]:.3f}', file=salida)
            print(f'MAP {self.metricas_total["average_precision"]:.3f}', file=salida)
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
    #Llamamos al evaluador con los ficheros
    evaluator.evaluate(qrels_file,results_file, output_file)
    #Sacamos la grafica
    evaluator.sacar_grafica()