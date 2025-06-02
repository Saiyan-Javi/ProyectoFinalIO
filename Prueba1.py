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
        self.root.title("Problema de Transporte / Asignación")

        # ----------------------------
        # Estructuras de datos
        # ----------------------------
        # Cada nodo: {
        #    "id": str,
        #    "x": float, "y": float,
        #    "supply": float, "demand": float,
        #    "fictitious": bool,
        #    "oval_id": int, "label_id": int,
        #    "value_rect_id": int, "value_text_id": int,
        #    "tag": str
        # }
        self.nodes = []

        # Cada arista: {
        #    "from": nodo_origen_id,
        #    "to": nodo_destino_id,
        #    "cost": float,
        #    "line_id": int, "rect_id": int, "text_id": int
        # }
        self.edges = []

        # Para gestionar arrastre de nodos
        self.drag_data = {
            "node": None,
            "x0": 0, "y0": 0
        }

        # ----------------------------
        # Panel de instrucciones
        # ----------------------------
        self.instruction_frame = ttk.Frame(root)
        self.instruction_frame.pack(fill=tk.X, pady=5)
        instrucciones = (
            "1. Clic izquierdo en el canvas para agregar nodos (azul → oferta, rojo → demanda).\n"
            "2. Seleccionar nodo con 'Seleccionar Nodo' y conectar a otro con costo.\n"
            "3. Clic derecho sobre nodo/arista para eliminar, modificar o cambiar ID.\n"
            "4. Arrastra un nodo (clic izquierdo + mover) para reubicarlo.\n"
            "5. Haz clic en 'Resolver' para Asignación o Transporte.\n"
            "6. Botón 'Limpiar' para borrar todo el canvas.\n"
            "\nLos nodos ficticios aparecen en gris, con oferta o demanda = diferencia."
        )
        ttk.Label(
            self.instruction_frame,
            text=instrucciones,
            font=("Helvetica", 9, "italic"),
            background="#f0f0f0",
            justify=tk.LEFT
        ).pack(padx=10, pady=5)

        # ----------------------------
        # Canvas para dibujar
        # ----------------------------
        self.canvas = tk.Canvas(root, width=600, height=450, bg="#f0f0f0",
                                highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(pady=10)
        # Clic izquierdo: agregar nodo o iniciar arrastre
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        # Clic derecho: opciones sobre nodo o arista
        self.canvas.bind("<Button-3>", self.canvas_options)

        # ----------------------------
        # Panel de controles (botones, entrada de costo)
        # ----------------------------
        self.control_frame = ttk.LabelFrame(root, text="Controles", padding=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Entrada para costo de arista
        ttk.Label(self.control_frame, text="Costo de Arista:").grid(row=0, column=0, padx=5, pady=5)
        self.cost_entry = ttk.Entry(self.control_frame)
        self.cost_entry.grid(row=0, column=1, padx=5, pady=5)
        self.cost_entry.insert(0, "0")

        # Botón Seleccionar Nodo
        self.select_btn = ttk.Button(self.control_frame, text="Seleccionar Nodo",
                                     command=self.select_node)
        self.select_btn.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # Botón Conectar Nodos
        self.connect_btn = ttk.Button(self.control_frame, text="Conectar Nodos",
                                      command=self.connect_nodes)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")

        # Botón Resolver
        self.solve_btn = ttk.Button(self.control_frame, text="Resolver",
                                    command=self.choose_problem_type, style="Accent.TButton")
        self.solve_btn.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        # Botón Limpiar
        self.clear_btn = ttk.Button(self.control_frame, text="Limpiar", command=self.clear_canvas)
        self.clear_btn.grid(row=1, column=2, columnspan=2, pady=5, sticky="ew")

        # Tooltips (opcionales)
        self.create_tooltip(self.select_btn, "Ingresa ID parcial para seleccionar un nodo.")
        self.create_tooltip(self.connect_btn, "Conecta el nodo seleccionado con otro de demanda.")
        self.create_tooltip(self.solve_btn, "Resuelve el modelo de Asignación o Transporte.")
        self.create_tooltip(self.clear_btn, "Borra todos los nodos y aristas del canvas.")

    # --------------------------------------------
    # Tooltip
    # --------------------------------------------
    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, background="#ffffe0",
                             relief="solid", borderwidth=1, font=("Helvetica", 8))
            label.pack()

        def hide_tooltip(event):
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    # --------------------------------------------
    # Limpia todo el canvas y estructura de datos
    # --------------------------------------------
    def clear_canvas(self):
        self.canvas.delete("all")
        self.nodes = []
        self.edges = []
        self.drag_data = {"node": None, "x0": 0, "y0": 0}
        messagebox.showinfo("Información", "Canvas limpiao. Puedes empezar de nuevo.")

    # --------------------------------------------
    # Al hacer clic izquierdo: agregar nodo o iniciar arrastre
    # --------------------------------------------
    def on_canvas_click(self, event):
        x, y = event.x, event.y

        # ¿Clic sobre un nodo?
        clicked_node = None
        for node in self.nodes:
            if math.hypot(node["x"] - x, node["y"] - y) <= 15:
                clicked_node = node
                break

        if clicked_node:
            # Iniciar arrastre
            self.drag_data["node"] = clicked_node
            self.drag_data["x0"] = x
            self.drag_data["y0"] = y
            self.canvas.bind("<B1-Motion>", self.do_drag)
            self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        else:
            # Si no hay nodo, agregar nuevo
            self.add_node(event)

    # --------------------------------------------
    # Durante arrastre (<B1-Motion>): mover nodo
    # --------------------------------------------
    def do_drag(self, event):
        node = self.drag_data["node"]
        if not node:
            return

        dx = event.x - self.drag_data["x0"]
        dy = event.y - self.drag_data["y0"]
        node["x"] += dx
        node["y"] += dy

        # Mover todos los objetos del nodo usando su tag
        self.canvas.move(node["tag"], dx, dy)

        # Actualizar aristas conectadas a este nodo
        self.update_edges_for_node(node)

        self.drag_data["x0"] = event.x
        self.drag_data["y0"] = event.y

    # --------------------------------------------
    # Al soltar (<ButtonRelease-1>): terminar arrastre
    # --------------------------------------------
    def end_drag(self, event):
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.drag_data["node"] = None

    # --------------------------------------------
    # Redibuja las aristas conectadas a `node`
    # --------------------------------------------
    def update_edges_for_node(self, node):
        for edge in self.edges:
            if edge["from"] == node["id"] or edge["to"] == node["id"]:
                n1 = next(n for n in self.nodes if n["id"] == edge["from"])
                n2 = next(n for n in self.nodes if n["id"] == edge["to"])
                x1, y1 = n1["x"], n1["y"]
                x2, y2 = n2["x"], n2["y"]

                # Mover línea
                self.canvas.coords(edge["line_id"], x1, y1, x2, y2)

                # Calcular nueva posición del texto de costo
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                length = math.hypot(dx, dy)
                if length != 0:
                    dx, dy = dx / length, dy / length
                perp_dx, perp_dy = -dy, dx
                text_x = mid_x + perp_dx * 15
                text_y = mid_y + perp_dy * 15
                text_x = max(30, min(text_x, 570))
                text_y = max(30, min(text_y, 420))

                self.canvas.coords(edge["rect_id"],
                                   text_x - 15, text_y - 8, text_x + 15, text_y + 8)
                self.canvas.coords(edge["text_id"], text_x, text_y)

    # --------------------------------------------
    # Dibuja un nodo completo (oval, etiqueta, recuadro, texto)
    # --------------------------------------------
    def draw_node(self, node):
        x, y = node["x"], node["y"]
        tag = node["id"]
        node["tag"] = tag

        if node.get("fictitious", False):
            fill_color = "#B0BEC5"
            label_text = f"{node['id'][:4]}\n({'O' if node['supply'] > 0 else 'D'} Fict.)"
            value_text = f"{'O:' + str(node['supply']) if node['supply'] > 0 else 'D:' + str(node['demand'])}"
        else:
            if node["supply"] > 0:
                fill_color = "#90CAF9"
                label_text = node["id"][:4]
                value_text = f"O:{node['supply']}"
            else:
                fill_color = "#EF9A9A"
                label_text = node["id"][:4]
                value_text = f"D:{node['demand']}"

        # Creamos círculo (oval)
        node["oval_id"] = self.canvas.create_oval(
            x - 15, y - 15, x + 15, y + 15,
            fill=fill_color, outline="#333333", width=2,
            tags=(tag,)
        )
        # Etiqueta con ID corto
        node["label_id"] = self.canvas.create_text(
            x, y - 25,
            text=label_text,
            fill="#333333",
            font=("Helvetica", 10, "bold"),
            tags=(tag,)
        )
        # Recuadro para valor
        node["value_rect_id"] = self.canvas.create_rectangle(
            x - 20, y + 7, x + 20, y + 23,
            fill="#ffffff", outline="", stipple="gray50",
            tags=(tag,)
        )
        # Texto con oferta o demanda
        node["value_text_id"] = self.canvas.create_text(
            x, y + 15,
            text=value_text,
            fill="#333333",
            font=("Helvetica", 9),
            tags=(tag,)
        )

    # --------------------------------------------
    # Dibuja una arista completa (línea + rectángulo + texto)
    # --------------------------------------------
    def draw_edge(self, edge):
        n1 = next(n for n in self.nodes if n["id"] == edge["from"])
        n2 = next(n for n in self.nodes if n["id"] == edge["to"])
        x1, y1 = n1["x"], n1["y"]
        x2, y2 = n2["x"], n2["y"]

        # Línea con flecha
        edge["line_id"] = self.canvas.create_line(
            x1, y1, x2, y2,
            arrow=tk.LAST, fill="#666666", width=2
        )

        # Calcular posición del texto
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length != 0:
            dx, dy = dx / length, dy / length
        perp_dx, perp_dy = -dy, dx
        text_x = mid_x + perp_dx * 15
        text_y = mid_y + perp_dy * 15
        text_x = max(30, min(text_x, 570))
        text_y = max(30, min(text_y, 420))

        edge["rect_id"] = self.canvas.create_rectangle(
            text_x - 15, text_y - 8, text_x + 15, text_y + 8,
            fill="#ffffff", outline="", stipple="gray50"
        )
        edge["text_id"] = self.canvas.create_text(
            text_x, text_y,
            text=str(edge["cost"]),
            fill="#333333",
            font=("Helvetica", 9)
        )

    # --------------------------------------------
    # Borra todo y redespliega nodos y aristas
    # --------------------------------------------
    def redraw_all(self):
        self.canvas.delete("all")
        for edge in self.edges:
            self.draw_edge(edge)
        for node in self.nodes:
            self.draw_node(node)

    # --------------------------------------------
    # Agregar un nuevo nodo en posición (event.x, event.y)
    # --------------------------------------------
    def add_node(self, event):
        x, y = event.x, event.y
        node_id = str(uuid.uuid4())[:8]
        is_supply = messagebox.askyesno("Tipo de Nodo", "¿Es un nodo de oferta?")

        if is_supply:
            supply = askfloat("Oferta", "Ingrese la oferta para este nodo:", parent=self.root, minvalue=0)
            if supply is None:
                return
            demand = 0
        else:
            demand = askfloat("Demanda", "Ingrese la demanda para este nodo:", parent=self.root, minvalue=0)
            if demand is None:
                return
            supply = 0

        nodo = {
            "id": node_id,
            "x": x, "y": y,
            "supply": supply, "demand": demand,
            "fictitious": False
        }
        self.nodes.append(nodo)
        self.draw_node(nodo)

    # --------------------------------------------
    # Seleccionar nodo por ID parcial para conectar
    # --------------------------------------------
    def select_node(self):
        node_id = askstring("Seleccionar Nodo", "Ingrese ID del nodo:", parent=self.root)
        if node_id:
            for node in self.nodes:
                if node["id"].startswith(node_id):
                    self.selected_node = node
                    messagebox.showinfo("Nodo Seleccionado", f"Nodo {node_id[:4]} seleccionado.")
                    break
            else:
                messagebox.showerror("Error", "Nodo no encontrado.")
        else:
            messagebox.showinfo("Información", "Selección cancelada.")

    # --------------------------------------------
    # Conectar el nodo seleccionado con otro de demanda
    # --------------------------------------------
    def connect_nodes(self):
        try:
            node_origen = self.selected_node
        except AttributeError:
            node_origen = None

        if not node_origen:
            messagebox.showerror("Error", "Seleccione un nodo primero.")
            return

        node2_id = askstring("Conectar Nodo", "Ingrese ID del nodo destino:", parent=self.root)
        if not node2_id:
            messagebox.showinfo("Información", "Conexión cancelada.")
            return

        try:
            cost = float(self.cost_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Ingrese un costo numérico válido.")
            return

        # Buscar nodo destino
        for nodo_dest in self.nodes:
            if nodo_dest["id"].startswith(node2_id):
                if node_origen["supply"] == 0 or nodo_dest["demand"] == 0:
                    messagebox.showerror("Error", "Debe conectar oferta → demanda.")
                    return
                edge = {
                    "from": node_origen["id"],
                    "to": nodo_dest["id"],
                    "cost": cost,
                    "line_id": None, "rect_id": None, "text_id": None
                }
                self.edges.append(edge)
                # Dibujarlo inmediatamente
                self.draw_edge(edge)
                break
        else:
            messagebox.showerror("Error", "Nodo destino no encontrado.")
            return

        # Limpiar selección
        self.selected_node = None

    # --------------------------------------------
    # Elegir tipo de problema: Asignación o Transporte
    # --------------------------------------------
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
        except tk.TclError:
            self.solve_transport()

    # --------------------------------------------
    # Resolver problema de asignación
    # --------------------------------------------
    def solve_assignment(self):
        supply_nodes = [n for n in self.nodes if n["supply"] > 0 and not n.get("fictitious", False)]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0 and not n.get("fictitious", False)]

        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda.")
            return

        if len(supply_nodes) != len(demand_nodes):
            messagebox.showerror("Error", "Para asignación, #ofertas = #demandas.")
            return

        # Limpiar resaltado previo
        for edge in self.edges:
            if edge.get("line_id") is not None:
                self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []

        # Forzar supply=1 y demand=1
        for s in supply_nodes: s["supply"] = 1
        for d in demand_nodes: d["demand"] = 1

        m = len(supply_nodes)
        n = len(demand_nodes)  # = m
        c = []
        A_eq = []
        b_eq = []

        result_text = "Función Objetivo (Asignación):\nMin Z = "
        cost_terms = []
        for i, s in enumerate(supply_nodes):
            for j, d in enumerate(demand_nodes):
                cost = next((e["cost"] for e in self.edges
                             if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta arista {s['id'][:4]} → {d['id'][:4]}.")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i + 1}{j + 1}")
        result_text += " + ".join(cost_terms) + "\n\n"

        # Restricciones agentes (fila=1)
        result_text += "Restricciones Agentes (≔1):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i + 1}{j + 1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} = 1 (Agente {supply_nodes[i]['id'][:4]})\n"

        # Restricciones tareas (columna=1)
        result_text += "\nRestricciones Tareas (≔1):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i + 1}{j + 1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = 1 (Tarea {demand_nodes[j]['id'][:4]})\n"

        result_text += "\nVariables binarias: " + ", ".join(
            [f"x_{i + 1}{j + 1}" for i in range(m) for j in range(n)]) + "\n\n"

        # Resolver con linprog
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0, 1), method="simplex")
        if res.success:
            solution = np.round(res.x.reshape(m, n))
            result_text += "Solución Óptima:\n"
            total_cost = 0
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    if solution[i][j] == 1:
                        cost = c[i * n + j]
                        result_text += f"{s['id'][:4]} → {d['id'][:4]}: costo {cost}\n"
                        total_cost += cost
                        edge = next((e for e in self.edges
                                     if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge.get("line_id") is not None:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
            result_text += f"Costo Total: {total_cost}\n"
            messagebox.showinfo("Resultado Asignación", result_text)
        else:
            messagebox.showerror("Error", "No se encontró solución óptima para asignación.")

    # --------------------------------------------
    # Resolver problema de transporte
    # --------------------------------------------
    def solve_transport(self):
        supply_nodes = [n for n in self.nodes if n["supply"] > 0 and not n.get("fictitious", False)]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0 and not n.get("fictitious", False)]

        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda.")
            return

        # Limpiar resaltado previo
        for edge in self.edges:
            if edge.get("line_id") is not None:
                self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []

        total_supply = sum(n["supply"] for n in supply_nodes)
        total_demand = sum(n["demand"] for n in demand_nodes)

        # Si demanda > oferta: nodo ficticio de oferta
        if total_supply < total_demand:
            shortfall = total_demand - total_supply
            fict_id = str(uuid.uuid4())[:8]
            x_fict, y_fict = 30, 30
            self.nodes.append({
                "id": fict_id,
                "x": x_fict, "y": y_fict,
                "supply": shortfall, "demand": 0,
                "fictitious": True
            })
            supply_nodes.append(self.nodes[-1])
            messagebox.showwarning(
                "Advertencia",
                f"Oferta total ({total_supply}) < Demanda total ({total_demand}).\n"
                f"Se agregó nodo ficticio de oferta con {shortfall} unidades."
            )
            # Dibujar nodo ficticio
            self.draw_node(self.nodes[-1])
            # Conectar con costo 0 a cada demanda real
            for d in demand_nodes:
                edge = {"from": fict_id, "to": d["id"], "cost": 0,
                        "line_id": None, "rect_id": None, "text_id": None}
                self.edges.append(edge)
                self.draw_edge(edge)

        # Si oferta > demanda: nodo ficticio de demanda
        elif total_supply > total_demand:
            excess = total_supply - total_demand
            fict_id = str(uuid.uuid4())[:8]
            x_fict, y_fict = 570, 420
            self.nodes.append({
                "id": fict_id,
                "x": x_fict, "y": y_fict,
                "supply": 0, "demand": excess,
                "fictitious": True
            })
            demand_nodes.append(self.nodes[-1])
            messagebox.showinfo(
                "Información",
                f"Oferta total ({total_supply}) > Demanda total ({total_demand}).\n"
                f"Se agregó nodo ficticio de demanda con {excess} unidades."
            )
            # Dibujar nodo ficticio
            self.draw_node(self.nodes[-1])
            # Conectar cada oferta real a este con costo 0
            for s in supply_nodes:
                edge = {"from": s["id"], "to": fict_id, "cost": 0,
                        "line_id": None, "rect_id": None, "text_id": None}
                self.edges.append(edge)
                self.draw_edge(edge)

        # Construir modelo
        supply_nodes = [n for n in self.nodes if n["supply"] > 0]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0]
        m = len(supply_nodes)
        n = len(demand_nodes)
        c = []
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []

        result_text = "Función Objetivo (Transporte):\nMin Z = "
        cost_terms = []
        for i, s in enumerate(supply_nodes):
            for j, d in enumerate(demand_nodes):
                cost = next((e["cost"] for e in self.edges
                             if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta arista {s['id'][:4]} → {d['id'][:4]}.")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i + 1}{j + 1}")
        result_text += " + ".join(cost_terms) + "\n\n"

        # Restricciones oferta (≤)
        result_text += "Restricciones Oferta (≤):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_ub.append(row)
            b_ub.append(supply_nodes[i]["supply"])
            terms = [f"x_{i + 1}{j + 1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} ≤ {supply_nodes[i]['supply']} (Planta {supply_nodes[i]['id'][:4]})\n"

        # Restricciones demanda (=)
        result_text += "\nRestricciones Demanda (=):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(demand_nodes[j]["demand"])
            terms = [f"x_{i + 1}{j + 1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = {demand_nodes[j]['demand']} (Comprador {demand_nodes[j]['id'][:4]})\n"

        result_text += "\nVariables x_{ij} ≥ 0\n\n"

        # Resolver con linprog
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub,
                      bounds=(0, None), method="simplex")
        if res.success:
            solution = res.x.reshape(m, n)
            result_text += "Solución Óptima:\n"
            total_cost = 0
            used_fict = False
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    qty = solution[i][j]
                    if qty > 0:
                        cost = c[i * n + j]
                        result_text += f"{s['id'][:4]} → {d['id'][:4]}: {qty} unidades, costo {cost * qty}\n"
                        total_cost += cost * qty
                        edge = next((e for e in self.edges
                                     if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge.get("line_id") is not None:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
                        if s.get("fictitious", False) or d.get("fictitious", False):
                            used_fict = True
            result_text += f"Costo Total: {total_cost}\n"
            if used_fict:
                result_text += "\nNota: Se usaron nodos ficticios, el modelo no estaba balanceado."
            messagebox.showinfo("Resultado Transporte", result_text)
        else:
            messagebox.showerror("Error", "No se encontró solución óptima para transporte.")

    # --------------------------------------------
    # Opciones clic derecho: eliminar/modificar/cambiarID nodo o arista
    # --------------------------------------------
    def canvas_options(self, event):
        x, y = event.x, event.y

        # 1) Detectar nodo
        clicked_node = None
        for node in self.nodes:
            if math.hypot(node["x"] - x, node["y"] - y) <= 15:
                clicked_node = node
                break

        if clicked_node:
            action = askstring(
                "Acción sobre Nodo",
                "Escriba:\n"
                "  • 'eliminar' para borrar el nodo,\n"
                "  • 'modificar' para cambiar oferta/demanda,\n"
                "  • 'cambiarid' para cambiar la identificación del nodo:",
                parent=self.root
            )
            if not action:
                return
            action = action.strip().lower()

            if action.startswith("elim"):
                # Eliminar nodo y aristas asociadas
                self.nodes = [n for n in self.nodes if n["id"] != clicked_node["id"]]
                self.edges = [e for e in self.edges
                              if e["from"] != clicked_node["id"] and e["to"] != clicked_node["id"]]
                messagebox.showinfo("Información", f"Nodo {clicked_node['id'][:4]} eliminado.")
                self.redraw_all()
                return

            elif action.startswith("mod"):
                # Modificar oferta o demanda (si no es ficticio)
                if clicked_node.get("fictitious", False):
                    messagebox.showerror("Error", "No se puede modificar nodo ficticio.")
                    return
                if clicked_node["supply"] > 0:
                    new_supply = askfloat(
                        "Modificar Oferta",
                        f"Oferta actual: {clicked_node['supply']}\nIngrese nueva oferta:",
                        parent=self.root, minvalue=0
                    )
                    if new_supply is None:
                        return
                    clicked_node["supply"] = new_supply
                    clicked_node["demand"] = 0
                    messagebox.showinfo("Información",
                                        f"Oferta nodo {clicked_node['id'][:4]} actualizada a {new_supply}.")
                else:
                    new_demand = askfloat(
                        "Modificar Demanda",
                        f"Demanda actual: {clicked_node['demand']}\nIngrese nueva demanda:",
                        parent=self.root, minvalue=0
                    )
                    if new_demand is None:
                        return
                    clicked_node["demand"] = new_demand
                    clicked_node["supply"] = 0
                    messagebox.showinfo("Información",
                                        f"Demanda nodo {clicked_node['id'][:4]} actualizada a {new_demand}.")
                self.redraw_all()
                return

            elif action.startswith("cambiarid"):
                old_id = clicked_node["id"]
                new_id = askstring(
                    "Cambiar ID",
                    f"ID actual: {old_id}\nIngrese nuevo ID único:",
                    parent=self.root
                )
                if not new_id:
                    return
                if any(n["id"] == new_id for n in self.nodes):
                    messagebox.showerror("Error", "Ese ID ya existe. Elija otro.")
                    return
                # Actualizar nodo y aristas
                clicked_node["id"] = new_id
                clicked_node["tag"] = new_id
                for e in self.edges:
                    if e["from"] == old_id: e["from"] = new_id
                    if e["to"] == old_id: e["to"] = new_id
                messagebox.showinfo("Información", f"ID cambiado de {old_id[:4]} a {new_id[:4]}.")
                self.redraw_all()
                return

            else:
                messagebox.showinfo("Información", "Acción no reconocida. Use 'eliminar', 'modificar' o 'cambiarid'.")
                return

        # 2) Detectar arista
        clicked_edge = self.find_edge_at(x, y)
        if clicked_edge:
            action = askstring(
                "Acción sobre Arista",
                "Escriba:\n"
                "  • 'eliminar' para borrar la arista,\n"
                "  • 'modificar' para cambiar el costo:",
                parent=self.root
            )
            if not action:
                return
            action = action.strip().lower()
            if action.startswith("elim"):
                self.edges = [
                    e for e in self.edges
                    if not (e["from"] == clicked_edge["from"] and e["to"] == clicked_edge["to"])
                ]
                messagebox.showinfo(
                    "Información",
                    f"Arista {clicked_edge['from'][:4]} → {clicked_edge['to'][:4]} eliminada."
                )
                self.redraw_all()
                return
            elif action.startswith("mod"):
                new_cost = askfloat(
                    "Modificar Costo de Arista",
                    f"Costo actual: {clicked_edge['cost']}\nIngrese nuevo costo:",
                    parent=self.root, minvalue=0
                )
                if new_cost is None:
                    return
                clicked_edge["cost"] = new_cost
                messagebox.showinfo(
                    "Información",
                    f"Costo arista {clicked_edge['from'][:4]} → {clicked_edge['to'][:4]} actualizado a {new_cost}."
                )
                self.redraw_all()
                return
            else:
                messagebox.showinfo("Información", "Acción no reconocida. Use 'eliminar' o 'modificar'.")
                return

    # --------------------------------------------
    # Busca arista cercana a (x, y) (dist ≤ 5 px)
    # --------------------------------------------
    def find_edge_at(self, x, y):
        for edge in self.edges:
            n1 = next((n for n in self.nodes if n["id"] == edge["from"]), None)
            n2 = next((n for n in self.nodes if n["id"] == edge["to"]), None)
            if not n1 or not n2:
                continue
            x1, y1 = n1["x"], n1["y"]
            x2, y2 = n2["x"], n2["y"]
            dx, dy = x2 - x1, y2 - y1
            if dx == dy == 0:
                dist = math.hypot(x - x1, y - y1)
            else:
                t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
                t = max(0, min(1, t))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = math.hypot(x - proj_x, y - proj_y)
            if dist <= 5:
                return edge
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = TransportProblemGUI(root)
    root.mainloop()
