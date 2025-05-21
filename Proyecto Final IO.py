import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.simpledialog import askstring, askfloat
import numpy as np
from scipy.optimize import linprog
import uuid
import math

class TransportProblemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Problema de Transporte")
        self.nodes = []
        self.edges = []
        self.selected_node = None
        self.solution_edges = []
        
        # Estilo
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 10), padding=5)
        self.style.configure("TLabel", font=("Helvetica", 10))
        
        # Panel de instrucciones
        self.instruction_frame = ttk.Frame(root)
        self.instruction_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            self.instruction_frame,
            text="1. Haz clic en el canvas para agregar plantas (azul) o compradores (rojo).\n"
                 "2. Selecciona un nodo y conéctalo a otro con un costo.\n"
                 "3. Haz clic en 'Resolver' para obtener la solución.",
            font=("Helvetica", 10, "italic"),
            background="#f0f0f0",
            justify=tk.LEFT
        ).pack(padx=10, pady=5)
        
        # Canvas para dibujar nodos y aristas (aumentado en altura)
        self.canvas = tk.Canvas(root, width=600, height=450, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.add_node)
        
        # Frame para controles
        self.control_frame = ttk.LabelFrame(root, text="Controles", padding=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Entrada para costo de arista
        ttk.Label(self.control_frame, text="Costo de Arista:").grid(row=0, column=0, padx=5, pady=5)
        self.cost_entry = ttk.Entry(self.control_frame)
        self.cost_entry.grid(row=0, column=1, padx=5, pady=5)
        self.cost_entry.insert(0, "0")
        
        # Botones
        self.select_btn = ttk.Button(self.control_frame, text="Seleccionar Nodo", command=self.select_node)
        self.select_btn.grid(row=1, column=0, columnspan=2, pady=5)
        
        self.connect_btn = ttk.Button(self.control_frame, text="Conectar Nodos", command=self.connect_nodes)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Botón Resolver 
        self.solve_btn = ttk.Button(self.control_frame, text="Resolver", command=self.choose_problem_type, style="Accent.TButton")
        self.solve_btn.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.clear_btn = ttk.Button(self.control_frame, text="Limpiar", command=self.clear_canvas)
        self.clear_btn.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Tooltips
        self.create_tooltip(self.select_btn, "Selecciona un nodo ingresando su ID.")
        self.create_tooltip(self.connect_btn, "Conecta dos nodos")
        self.create_tooltip(self.solve_btn, "Resuelve el problema de transporte.")
        self.create_tooltip(self.clear_btn, "Limpia el canvas y empieza de nuevo.")
        
    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("Helvetica", 8))
            label.pack()
        
        def hide_tooltip(event):
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def add_node(self, event):
        x, y = event.x, event.y
        node_id = str(uuid.uuid4())[:8]
        is_supply = messagebox.askyesno("Tipo de Nodo", "¿Es un nodo de oferta?")
        
        if is_supply:
            supply = askfloat("Oferta", "Ingrese la oferta para este nodo:", parent=self.root, minvalue=0)
            if supply is None:
                messagebox.showinfo("Información", "Creación de nodo cancelada")
                return
            demand = 0
        else:
            demand = askfloat("Demanda", "Ingrese la demanda para este nodo:", parent=self.root, minvalue=0)
            if demand is None:
                messagebox.showinfo("Información", "Creación de nodo cancelada")
                return
            supply = 0
        
        self.nodes.append({"id": node_id, "x": x, "y": y, "supply": supply, "demand": demand})
        fill_color = "#90CAF9" if is_supply else "#EF9A9A"
        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill=fill_color, outline="#333333", width=2)
        self.canvas.create_text(x, y-25, text=node_id[:4], fill="#333333", font=("Helvetica", 10, "bold"))
        value_text = f"{'O:'+str(supply) if is_supply else 'D:'+str(demand)}"
        self.canvas.create_rectangle(
            x-20, y+15-8, x+20, y+15+8, fill="#ffffff", outline="", stipple="gray50"
        )
        self.canvas.create_text(x, y+15, text=value_text, fill="#333333", font=("Helvetica", 9))
    
    def clear_canvas(self):
        self.canvas.delete("all")
        self.nodes = []
        self.edges = []
        self.selected_node = None
        self.solution_edges = []
        messagebox.showinfo("Información", "Canvas limpiado. Puedes empezar de nuevo.")
    
    def select_node(self):
        node_id = askstring("Seleccionar Nodo", "Ingrese ID del nodo:", parent=self.root)
        if node_id:
            for node in self.nodes:
                if node["id"].startswith(node_id):
                    self.selected_node = node
                    messagebox.showinfo("Nodo Seleccionado", f"Nodo {node_id} seleccionado")
                    break
            else:
                messagebox.showerror("Error", "Nodo no encontrado")
        else:
            messagebox.showinfo("Información", "Selección cancelada")
    
    def connect_nodes(self):
        if not self.selected_node:
            messagebox.showerror("Error", "Seleccione un nodo primero")
            return
        node2_id = askstring("Conectar Nodo", "Ingrese ID del nodo destino:", parent=self.root)
        if not node2_id:
            messagebox.showinfo("Información", "Conexión cancelada")
            return
        try:
            cost = float(self.cost_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Ingrese un costo numérico válido")
            return
        
        for node2 in self.nodes:
            if node2["id"].startswith(node2_id):
                if self.selected_node["supply"] == 0 or node2["demand"] == 0:
                    messagebox.showerror("Error", "Debe conectar un nodo de oferta a un nodo de demanda")
                    return
                edge = {
                    "from": self.selected_node["id"],
                    "to": node2["id"],
                    "cost": cost,
                    "line_id": None,
                    "text_id": None,
                    "rect_id": None
                }
                self.edges.append(edge)
                line_id = self.canvas.create_line(
                    self.selected_node["x"], self.selected_node["y"],
                    node2["x"], node2["y"],
                    arrow=tk.LAST, fill="#666666", width=2
                )
                edge["line_id"] = line_id
                
                # Calcular posición del texto desplazada
                x1, y1 = self.selected_node["x"], self.selected_node["y"]
                x2, y2 = node2["x"], node2["y"]
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                length = math.sqrt(dx**2 + dy**2)
                if length != 0:
                    dx, dy = dx / length, dy / length
                perp_dx, perp_dy = -dy, dx
                offset = 15
                text_x = mid_x + perp_dx * offset
                text_y = mid_y + perp_dy * offset
                text_x = max(30, min(text_x, 570))
                text_y = max(30, min(text_y, 420))
                rect_id = self.canvas.create_rectangle(
                    text_x-15, text_y-8, text_x+15, text_y+8,
                    fill="#ffffff", outline="", stipple="gray50"
                )
                text_id = self.canvas.create_text(
                    text_x, text_y,
                    text=str(cost), fill="#333333", font=("Helvetica", 9)
                )
                edge["rect_id"] = rect_id
                edge["text_id"] = text_id
                break
        else:
            messagebox.showerror("Error", "Nodo destino no encontrado")
            return
        self.selected_node = None
    
    def choose_problem_type(self):
        try:
            problem_type = messagebox.askyesno(
                "Seleccionar Tipo de Problema",
                "¿Desea resolver un Problema de Asignación? (Sí = Asignación, No = Transporte)",
                parent=self.root
            )
            if problem_type:
                self.solve_assignment()
            else:
                self.solve_transport()
        except tk.TclError as e:
            messagebox.showerror("Error", f"No se pudo mostrar el cuadro de diálogo: {e}\nSe usará el método de Transporte por defecto.")
            self.solve_transport()

    def solve_assignment(self):
        supply_nodes = [n for n in self.nodes if n["supply"] > 0]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0]
        
        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda")
            return
        
        # Para un problema de asignación, el número de agentes y tareas debe ser igual
        if len(supply_nodes) != len(demand_nodes):
            messagebox.showerror("Error", "El número de nodos de oferta y demanda debe ser igual para un problema de asignación")
            return
        
        # Limpiar resaltado anterior
        for edge in self.edges:
            self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []
        
        # Forzar oferta y demanda a 1 para cada nodo (característica del problema de asignación)
        for s in supply_nodes:
            s["supply"] = 1
        for d in demand_nodes:
            d["demand"] = 1
        
        m = len(supply_nodes)
        n = len(demand_nodes)  # m == n
        
        c = []
        A_eq = []
        b_eq = []
        
        # Construir matriz de costos
        result_text = "Función Objetivo (Asignación):\nMin Z = "
        cost_terms = []
        for i, s in enumerate(supply_nodes):
            for j, d in enumerate(demand_nodes):
                cost = next((e["cost"] for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta la arista de {s['id'][:4]} a {d['id'][:4]}")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i+1}{j+1}")
        result_text += " + ".join(cost_terms) + "\n\n"
        
        # Restricciones: cada agente se asigna a una sola tarea (suma de cada fila = 1)
        result_text += "Restricciones de Agentes (suma por fila = 1):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i+1}{j+1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} = 1 (Agente {supply_nodes[i]['id'][:4]})\n"
        
        # Restricciones: cada tarea se asigna a un solo agente (suma de cada columna = 1)
        result_text += "\nRestricciones de Tareas (suma por columna = 1):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i+1}{j+1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = 1 (Tarea {demand_nodes[j]['id'][:4]})\n"
        
        # Restricciones de no negatividad y binarias
        result_text += "\nRestricciones de Asignación:\n"
        result_text += ", ".join([f"x_{i+1}{j+1} ∈ {{0, 1}}" for i in range(m) for j in range(n)]) + "\n\n"
        
        # Resolver usando linprog (forzando variables binarias con límites 0 y 1)
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0, 1), method="simplex")
        
        if res.success:
            solution = np.round(res.x.reshape(m, n))  # Redondear para asegurar 0 o 1
            result_text += "Solución Óptima (Asignación):\n"
            total_cost = 0
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    if solution[i][j] == 1:
                        cost = c[i * n + j]
                        result_text += f"Agente {s['id'][:4]} asignado a Tarea {d['id'][:4]}: costo {cost}\n"
                        total_cost += cost
                        edge = next((e for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge["line_id"]:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
                            self.solution_edges.append(edge)
            result_text += f"Costo Total: {total_cost}\n"
            messagebox.showinfo("Resultado", result_text)
        else:
            messagebox.showerror("Error", "No se pudo encontrar una solución óptima para el problema de asignación")

    def solve_transport(self):
        supply_nodes = [n for n in self.nodes if n["supply"] > 0]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0]
        
        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda")
            return
        
        # Limpiar resaltado anterior
        for edge in self.edges:
            self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []
        
        # Calcular oferta y demanda totales
        total_supply = sum(n["supply"] for n in supply_nodes)
        total_demand = sum(n["demand"] for n in demand_nodes)
        
        # Programación defensiva
        if total_supply < total_demand:
            shortfall = total_demand - total_supply
            fict_node_id = str(uuid.uuid4())[:8]
            supply_nodes.append({
                "id": fict_node_id,
                "x": 0,
                "y": 0,
                "supply": shortfall,
                "demand": 0
            })
            messagebox.showwarning(
                "Advertencia",
                f"La oferta total ({total_supply}) es menor que la demanda total ({total_demand}). "
                f"Se agregó un nodo ficticio de oferta con {shortfall} unidades."
            )
            for d in demand_nodes:
                self.edges.append({
                    "from": fict_node_id,
                    "to": d["id"],
                    "cost": 10000,
                    "line_id": None,
                    "text_id": None,
                    "rect_id": None
                })
        elif total_supply > total_demand:
            messagebox.showinfo(
                "Información",
                f"La oferta total ({total_supply}) es mayor que la demanda total ({total_demand}). "
                "El exceso de oferta no se utilizará."
            )
        
        m, n = len(supply_nodes), len(demand_nodes)
        c = []
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []
        
        # Construir matriz de costos y función objetivo
        result_text = "Función Objetivo:\nMin Z = "
        cost_terms = []
        for i, s in enumerate(supply_nodes):
            for j, d in enumerate(demand_nodes):
                cost = next((e["cost"] for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta la arista de {s['id'][:4]} a {d['id'][:4]}")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i+1}{j+1}")
        result_text += " + ".join(cost_terms) + "\n\n"
        
        # Restricciones de oferta (menor o igual)
        result_text += "Restricciones de Oferta (≤):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_ub.append(row)
            b_ub.append(supply_nodes[i]["supply"])
            terms = [f"x_{i+1}{j+1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} ≤ {supply_nodes[i]['supply']} (Planta {supply_nodes[i]['id'][:4]})\n"
        
        # Restricciones de demanda (igual)
        result_text += "\nRestricciones de Demanda (=):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(demand_nodes[j]["demand"])
            terms = [f"x_{i+1}{j+1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = {demand_nodes[j]['demand']} (Comprador {demand_nodes[j]['id'][:4]})\n"
        
        # Restricciones de no negatividad
        result_text += "\nRestricciones de No Negatividad:\n"
        result_text += ", ".join([f"x_{i+1}{j+1} ≥ 0" for i in range(m) for j in range(n)]) + "\n\n"
        
        # Resolver usando linprog
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="simplex")
        
        if res.success:
            solution = res.x.reshape(m, n)
            result_text += "Solución Óptima:\n"
            total_cost = 0
            used_fictitious = False
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    if solution[i][j] > 0:
                        cost = c[i * n + j]
                        result_text += f"De {s['id'][:4]} a {d['id'][:4]}: {solution[i][j]} unidades, costo: {cost * solution[i][j]}\n"
                        total_cost += cost * solution[i][j]
                        edge = next((e for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge["line_id"]:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
                            self.solution_edges.append(edge)
                        if s["id"] in [n["id"] for n in supply_nodes if n["x"] == 0 and n["y"] == 0]:
                            used_fictitious = True
            result_text += f"Costo Total: {total_cost}\n"
            if used_fictitious:
                result_text += "Nota: Se usó el nodo ficticio, indicando que no se puede satisfacer toda la demanda."
            messagebox.showinfo("Resultado", result_text)
        else:
            messagebox.showerror("Error", "No se pudo encontrar una solución óptima")

if __name__ == "__main__":
    root = tk.Tk()
    app = TransportProblemGUI(root)
    root.mainloop()