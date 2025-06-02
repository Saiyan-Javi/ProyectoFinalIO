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
        self.nodes = []  # Cada nodo: {id, x, y, supply, demand, fictitious}
        self.edges = []  # Cada arista: {from, to, cost, line_id, text_id, rect_id}
        self.solution_edges = []
        self.selected_node = None

        # Estilos
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 10), padding=5)
        self.style.configure("TLabel", font=("Helvetica", 10))

        # Panel de instrucciones
        self.instruction_frame = ttk.Frame(root)
        self.instruction_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            self.instruction_frame,
            text=(
                "1. Haz clic izquierdo en el canvas para agregar plantas (azul) o compradores (rojo).\n"
                "2. Selecciona un nodo con 'Seleccionar Nodo' y conéctalo a otro con un costo.\n"
                "3. Haz clic en 'Resolver' para obtener la solución.\n"
                "4. Clic derecho sobre un nodo o una arista para eliminar o modificar.\n"
                "\nLos nodos ficticios (si se crean) aparecen en gris."
            ),
            font=("Helvetica", 10, "italic"),
            background="#f0f0f0",
            justify=tk.LEFT
        ).pack(padx=10, pady=5)

        # Canvas para dibujar nodos y aristas
        self.canvas = tk.Canvas(root, width=600, height=450, bg="#f0f0f0", highlightthickness=1,
                                highlightbackground="#cccccc")
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.add_node)  # clic izquierdo para añadir nodo
        self.canvas.bind("<Button-3>", self.canvas_options)  # clic derecho para opciones nodo/arista

        # Frame para controles
        self.control_frame = ttk.LabelFrame(root, text="Controles", padding=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Entrada para costo de arista
        ttk.Label(self.control_frame, text="Costo de Arista:").grid(row=0, column=0, padx=5, pady=5)
        self.cost_entry = ttk.Entry(self.control_frame)
        self.cost_entry.grid(row=0, column=1, padx=5, pady=5)
        self.cost_entry.insert(0, "0")

        # Botones de selección/conexión
        self.select_btn = ttk.Button(self.control_frame, text="Seleccionar Nodo", command=self.select_node)
        self.select_btn.grid(row=1, column=0, columnspan=2, pady=5)

        self.connect_btn = ttk.Button(self.control_frame, text="Conectar Nodos", command=self.connect_nodes)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=5)

        # Botón Resolver
        self.solve_btn = ttk.Button(self.control_frame, text="Resolver", command=self.choose_problem_type,
                                    style="Accent.TButton")
        self.solve_btn.grid(row=3, column=0, columnspan=2, pady=5)

        self.clear_btn = ttk.Button(self.control_frame, text="Limpiar", command=self.clear_canvas)
        self.clear_btn.grid(row=4, column=0, columnspan=2, pady=5)

        # Tooltips
        self.create_tooltip(self.select_btn, "Selecciona un nodo ingresando su ID.")
        self.create_tooltip(self.connect_btn, "Conecta dos nodos.")
        self.create_tooltip(self.solve_btn, "Resuelve el problema de transporte o asignación.")
        self.create_tooltip(self.clear_btn, "Limpia el canvas y comienza de nuevo.")

    def create_tooltip(self, widget, text):
        """Muestra un tooltip al pasar el cursor por encima del widget."""

        def show_tooltip(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1,
                             font=("Helvetica", 8))
            label.pack()

        def hide_tooltip(event):
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def add_node(self, event):
        """Agrega un nodo (oferta o demanda) al hacer clic izquierdo en el canvas."""
        x, y = event.x, event.y
        node_id = str(uuid.uuid4())[:8]
        is_supply = messagebox.askyesno("Tipo de Nodo", "¿Es un nodo de oferta?")

        if is_supply:
            supply = askfloat("Oferta", "Ingrese la oferta para este nodo:", parent=self.root, minvalue=0)
            if supply is None:
                messagebox.showinfo("Información", "Creación de nodo cancelada.")
                return
            demand = 0
            fill_color = "#90CAF9"  # Azul para oferta real
        else:
            demand = askfloat("Demanda", "Ingrese la demanda para este nodo:", parent=self.root, minvalue=0)
            if demand is None:
                messagebox.showinfo("Información", "Creación de nodo cancelada.")
                return
            supply = 0
            fill_color = "#EF9A9A"  # Rojo para demanda real

        # Agregar a la lista de nodos
        self.nodes.append({
            "id": node_id,
            "x": x,
            "y": y,
            "supply": supply,
            "demand": demand,
            "fictitious": False
        })

        # Dibujar nodo en el canvas
        self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=fill_color, outline="#333333", width=2)
        self.canvas.create_text(x, y - 25, text=node_id[:4], fill="#333333", font=("Helvetica", 10, "bold"))
        value_text = f"{'O:' + str(supply) if is_supply else 'D:' + str(demand)}"
        self.canvas.create_rectangle(x - 20, y + 7, x + 20, y + 23, fill="#ffffff", outline="", stipple="gray50")
        self.canvas.create_text(x, y + 15, text=value_text, fill="#333333", font=("Helvetica", 9))

    def clear_canvas(self):
        """Borra todos los dibujos y reinicia las estructuras de datos."""
        self.canvas.delete("all")
        self.nodes = []
        self.edges = []
        self.selected_node = None
        self.solution_edges = []
        messagebox.showinfo("Información", "Canvas limpiado. Puedes comenzar de nuevo.")

    def select_node(self):
        """Selecciona un nodo buscando por ID (muestra un cuadro de diálogo)."""
        node_id = askstring("Seleccionar Nodo", "Ingrese ID del nodo:", parent=self.root)
        if node_id:
            for node in self.nodes:
                if node["id"].startswith(node_id):
                    self.selected_node = node
                    messagebox.showinfo("Nodo Seleccionado", f"Nodo {node_id} seleccionado.")
                    break
            else:
                messagebox.showerror("Error", "Nodo no encontrado.")
        else:
            messagebox.showinfo("Información", "Selección cancelada.")

    def connect_nodes(self):
        """Conecta el nodo previamente seleccionado con otro nodo de demanda, asignando un costo."""
        if not self.selected_node:
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

        for node2 in self.nodes:
            if node2["id"].startswith(node2_id):
                # Solo conectar oferta → demanda (nodos reales)
                if self.selected_node["supply"] == 0 or node2["demand"] == 0:
                    messagebox.showerror("Error", "Debe conectar un nodo de oferta a un nodo de demanda.")
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
                # Dibujar la línea con flecha
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
                length = math.hypot(dx, dy)
                if length != 0:
                    dx, dy = dx / length, dy / length
                perp_dx, perp_dy = -dy, dx
                offset = 15
                text_x = mid_x + perp_dx * offset
                text_y = mid_y + perp_dy * offset
                text_x = max(30, min(text_x, 570))
                text_y = max(30, min(text_y, 420))

                rect_id = self.canvas.create_rectangle(
                    text_x - 15, text_y - 8, text_x + 15, text_y + 8,
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
            messagebox.showerror("Error", "Nodo destino no encontrado.")
            return
        self.selected_node = None

    def canvas_options(self, event):
        """
        Se activa con clic derecho. Primero intenta detectar si se hizo clic sobre un nodo;
        si no es un nodo, verifica si se hizo clic sobre una arista. Luego permite eliminar
        o modificar según corresponda.
        """
        x_click, y_click = event.x, event.y

        # 1) Intentar detectar nodo
        clicked_node = None
        for node in self.nodes:
            dist = math.hypot(node["x"] - x_click, node["y"] - y_click)
            if dist <= 15:
                clicked_node = node
                break

        if clicked_node:
            # Misma lógica que antes para nodos
            action = askstring(
                "Acción sobre Nodo",
                "Ingrese 'eliminar' para borrar el nodo,\no 'modificar' para cambiar oferta/demanda:",
                parent=self.root
            )
            if not action:
                return
            action = action.strip().lower()
            if action.startswith("elim"):
                # Eliminar nodo y todas sus aristas
                self.nodes = [n for n in self.nodes if n["id"] != clicked_node["id"]]
                self.edges = [e for e in self.edges if
                              e["from"] != clicked_node["id"] and e["to"] != clicked_node["id"]]
                messagebox.showinfo("Información", f"Nodo {clicked_node['id'][:4]} eliminado.")
                self.redraw_all()
            elif action.startswith("mod"):
                if clicked_node.get("fictitious", False):
                    messagebox.showerror("Error", "No se puede modificar un nodo ficticio.")
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
                                        f"Oferta de nodo {clicked_node['id'][:4]} actualizada a {new_supply}.")
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
                                        f"Demanda de nodo {clicked_node['id'][:4]} actualizada a {new_demand}.")
                self.redraw_all()
            else:
                messagebox.showinfo("Información", "Acción no reconocida. Use 'eliminar' o 'modificar'.")
            return

        # 2) Si no es nodo, intentar detectar arista
        clicked_edge = self.find_edge_at(x_click, y_click)
        if clicked_edge:
            action = askstring(
                "Acción sobre Arista",
                "Ingrese 'eliminar' para borrar la arista,\no 'modificar' para cambiar su costo:",
                parent=self.root
            )
            if not action:
                return
            action = action.strip().lower()
            if action.startswith("elim"):
                # Eliminar arista
                self.edges = [e for e in self.edges if
                              not (e["from"] == clicked_edge["from"] and e["to"] == clicked_edge["to"])]
                messagebox.showinfo(
                    "Información",
                    f"Arista {clicked_edge['from'][:4]} → {clicked_edge['to'][:4]} eliminada."
                )
                self.redraw_all()
            elif action.startswith("mod"):
                # Modificar costo
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
                    f"Costo de arista {clicked_edge['from'][:4]} → {clicked_edge['to'][:4]} actualizado a {new_cost}."
                )
                self.redraw_all()
            else:
                messagebox.showinfo("Información", "Acción no reconocida. Use 'eliminar' o 'modificar'.")
            return

    def find_edge_at(self, x, y):
        """
        Recorre todas las aristas y devuelve la primera cuyo segmento (from → to)
        esté a ≤ 5 píxeles del punto (x,y). Si no encuentra ninguna, devuelve None.
        """
        for edge in self.edges:
            n1 = next((n for n in self.nodes if n["id"] == edge["from"]), None)
            n2 = next((n for n in self.nodes if n["id"] == edge["to"]), None)
            if not n1 or not n2:
                continue
            x1, y1 = n1["x"], n1["y"]
            x2, y2 = n2["x"], n2["y"]
            # Distancia punto a segmento:
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

    def redraw_all(self):
        """Borra todo y vuelve a dibujar nodos y aristas según las listas self.nodes y self.edges."""
        self.canvas.delete("all")

        # 1) Dibujar aristas
        for edge in self.edges:
            from_node = next((n for n in self.nodes if n["id"] == edge["from"]), None)
            to_node = next((n for n in self.nodes if n["id"] == edge["to"]), None)
            if not from_node or not to_node:
                continue

            line_id = self.canvas.create_line(
                from_node["x"], from_node["y"],
                to_node["x"], to_node["y"],
                arrow=tk.LAST, fill="#666666", width=2
            )
            edge["line_id"] = line_id

            # Texto desplazado de costo
            x1, y1 = from_node["x"], from_node["y"]
            x2, y2 = to_node["x"], to_node["y"]
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length != 0:
                dx, dy = dx / length, dy / length
            perp_dx, perp_dy = -dy, dx
            offset = 15
            text_x = mid_x + perp_dx * offset
            text_y = mid_y + perp_dy * offset
            text_x = max(30, min(text_x, 570))
            text_y = max(30, min(text_y, 420))

            rect_id = self.canvas.create_rectangle(
                text_x - 15, text_y - 8, text_x + 15, text_y + 8,
                fill="#ffffff", outline="", stipple="gray50"
            )
            text_id = self.canvas.create_text(
                text_x, text_y,
                text=str(edge["cost"]), fill="#333333", font=("Helvetica", 9)
            )
            edge["rect_id"] = rect_id
            edge["text_id"] = text_id

        # 2) Dibujar nodos
        for node in self.nodes:
            x, y = node["x"], node["y"]
            if node.get("fictitious", False):
                fill_color = "#B0BEC5"  # Gris para ficticios
                label = f"{node['id'][:4]}\n({'O' if node['supply'] > 0 else 'D'} Fict.)"
                value_text = f"{'O:' + str(node['supply']) if node['supply'] > 0 else 'D:' + str(node['demand'])}"
            else:
                if node["supply"] > 0:
                    fill_color = "#90CAF9"  # Azul real
                    label = node["id"][:4]
                    value_text = f"O:{node['supply']}"
                else:
                    fill_color = "#EF9A9A"  # Rojo real
                    label = node["id"][:4]
                    value_text = f"D:{node['demand']}"

            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=fill_color, outline="#333333", width=2)
            self.canvas.create_text(x, y - 25, text=label, fill="#333333", font=("Helvetica", 10, "bold"))
            self.canvas.create_rectangle(x - 20, y + 7, x + 20, y + 23, fill="#ffffff", outline="", stipple="gray50")
            self.canvas.create_text(x, y + 15, text=value_text, fill="#333333", font=("Helvetica", 9))

    def choose_problem_type(self):
        """Pregunta si el usuario quiere resolver asignación o transporte."""
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
            messagebox.showerror("Error",
                                 f"No se pudo mostrar el cuadro de diálogo: {e}\nSe usará transporte por defecto.")
            self.solve_transport()

    def solve_assignment(self):
        """Resuelve el problema de asignación: cada oferta se asigna exactamente a una demanda."""
        supply_nodes = [n for n in self.nodes if n["supply"] > 0 and not n.get("fictitious", False)]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0 and not n.get("fictitious", False)]

        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda.")
            return

        # Para asignación, número de agentes (ofertas) = número de tareas (demandas)
        if len(supply_nodes) != len(demand_nodes):
            messagebox.showerror("Error", "El número de ofertas y demandas debe ser igual para asignación.")
            return

        # Limpiar resaltado anterior
        for edge in self.edges:
            if edge.get("line_id") is not None:
                self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []

        # Forzar supply=1 y demand=1 para cada nodo real
        for s in supply_nodes:
            s["supply"] = 1
        for d in demand_nodes:
            d["demand"] = 1

        m = len(supply_nodes)
        n = len(demand_nodes)  # m == n

        c = []
        A_eq = []
        b_eq = []

        result_text = "Función Objetivo (Asignación):\nMin Z = "
        cost_terms = []
        for i, s in enumerate(supply_nodes):
            for j, d in enumerate(demand_nodes):
                cost = next((e["cost"] for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta la arista de {s['id'][:4]} a {d['id'][:4]}.")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i + 1}{j + 1}")
        result_text += " + ".join(cost_terms) + "\n\n"

        # Restricciones de agentes (fila = 1)
        result_text += "Restricciones de Agentes (suma por fila = 1):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i + 1}{j + 1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} = 1 (Agente {supply_nodes[i]['id'][:4]})\n"

        # Restricciones de tareas (columna = 1)
        result_text += "\nRestricciones de Tareas (suma por columna = 1):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(1)
            terms = [f"x_{i + 1}{j + 1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = 1 (Tarea {demand_nodes[j]['id'][:4]})\n"

        # Restricciones de no negatividad y binarias
        result_text += "\nRestricciones de Asignación:\n"
        result_text += ", ".join([f"x_{i + 1}{j + 1} ∈ {{0,1}}" for i in range(m) for j in range(n)]) + "\n\n"

        # Resolver con linprog (simplex), forzando 0 ≤ x ≤ 1
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0, 1), method="simplex")

        if res.success:
            solution = np.round(res.x.reshape(m, n))  # Redondear a 0 o 1
            result_text += "Solución Óptima (Asignación):\n"
            total_cost = 0
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    if solution[i][j] == 1:
                        cost = c[i * n + j]
                        result_text += f"Agente {s['id'][:4]} → Tarea {d['id'][:4]}: costo {cost}\n"
                        total_cost += cost
                        edge = next((e for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge.get("line_id") is not None:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
                            self.solution_edges.append(edge)
            result_text += f"Costo Total: {total_cost}\n"
            messagebox.showinfo("Resultado Asignación", result_text)
        else:
            messagebox.showerror("Error", "No se encontró solución óptima para asignación.")

    def solve_transport(self):
        """
        Resuelve el problema de transporte. Si total_supply < total_demand,
        agrega nodo ficticio de oferta (conecta con cada demanda real a costo = 0);
        si total_supply > total_demand, agrega nodo ficticio de demanda
        (conecta con cada oferta real a costo = 0). Luego construye y resuelve el modelo.
        """
        supply_nodes = [n for n in self.nodes if n["supply"] > 0 and not n.get("fictitious", False)]
        demand_nodes = [n for n in self.nodes if n["demand"] > 0 and not n.get("fictitious", False)]

        if not supply_nodes or not demand_nodes:
            messagebox.showerror("Error", "Debe haber al menos un nodo de oferta y uno de demanda.")
            return

        # Limpiar resaltado de aristas anteriores
        for edge in self.edges:
            if edge.get("line_id") is not None:
                self.canvas.itemconfig(edge["line_id"], fill="#666666", width=2)
        self.solution_edges = []

        total_supply = sum(n["supply"] for n in supply_nodes)
        total_demand = sum(n["demand"] for n in demand_nodes)

        # --- Si demanda > oferta, agregar nodo ficticio de oferta ---
        if total_supply < total_demand:
            shortfall = total_demand - total_supply
            fict_id = str(uuid.uuid4())[:8]
            x_fict, y_fict = 30, 30  # Posición arbitraria para el nodo ficticio
            self.nodes.append({
                "id": fict_id,
                "x": x_fict,
                "y": y_fict,
                "supply": shortfall,
                "demand": 0,
                "fictitious": True
            })
            supply_nodes.append(self.nodes[-1])
            messagebox.showwarning(
                "Advertencia",
                f"La oferta total ({total_supply}) es menor que la demanda total ({total_demand}).\n"
                f"Se agregó un nodo ficticio de oferta con {shortfall} unidades."
            )
            # Dibujar nodo ficticio (gris)
            self.canvas.create_oval(x_fict - 15, y_fict - 15, x_fict + 15, y_fict + 15, fill="#B0BEC5",
                                    outline="#333333", width=2)
            self.canvas.create_text(x_fict, y_fict - 30, text=f"{fict_id[:4]}\n(Of. Fict.)", fill="#333333",
                                    font=("Helvetica", 9, "bold"))
            self.canvas.create_rectangle(x_fict - 20, y_fict + 7, x_fict + 20, y_fict + 23, fill="#ffffff", outline="",
                                         stipple="gray50")
            self.canvas.create_text(x_fict, y_fict + 15, text=f"O:{shortfall}", fill="#333333", font=("Helvetica", 9))
            # Agregar aristas de costo 0 desde este ficticio a cada demanda real
            for d in demand_nodes:
                self.edges.append({
                    "from": fict_id,
                    "to": d["id"],
                    "cost": 0,
                    "line_id": None,
                    "text_id": None,
                    "rect_id": None
                })
            # --- REDIBUJAR TODO PARA MOSTRAR ARISTAS FICTICIAS ---
            self.redraw_all()

        # --- Si oferta > demanda, agregar nodo ficticio de demanda ---
        elif total_supply > total_demand:
            excess = total_supply - total_demand
            fict_id = str(uuid.uuid4())[:8]
            x_fict, y_fict = 570, 420  # Posición arbitraria para el nodo ficticio
            self.nodes.append({
                "id": fict_id,
                "x": x_fict,
                "y": y_fict,
                "supply": 0,
                "demand": excess,
                "fictitious": True
            })
            demand_nodes.append(self.nodes[-1])
            messagebox.showinfo(
                "Información",
                f"La oferta total ({total_supply}) es mayor que la demanda total ({total_demand}).\n"
                f"Se agregó un nodo ficticio de demanda con {excess} unidades."
            )
            # Dibujar nodo ficticio (gris)
            self.canvas.create_oval(x_fict - 15, y_fict - 15, x_fict + 15, y_fict + 15, fill="#B0BEC5",
                                    outline="#333333", width=2)
            self.canvas.create_text(x_fict, y_fict - 30, text=f"{fict_id[:4]}\n(Dem. Fict.)", fill="#333333",
                                    font=("Helvetica", 9, "bold"))
            self.canvas.create_rectangle(x_fict - 20, y_fict + 7, x_fict + 20, y_fict + 23, fill="#ffffff", outline="",
                                         stipple="gray50")
            self.canvas.create_text(x_fict, y_fict + 15, text=f"D:{excess}", fill="#333333", font=("Helvetica", 9))
            # Agregar aristas de costo 0 desde cada oferta real a este ficticio
            for s in supply_nodes:
                self.edges.append({
                    "from": s["id"],
                    "to": fict_id,
                    "cost": 0,
                    "line_id": None,
                    "text_id": None,
                    "rect_id": None
                })
            # --- REDIBUJAR TODO PARA MOSTRAR ARISTAS FICTICIAS ---
            self.redraw_all()

        # Reconstruir el modelo con supply_nodes y demand_nodes (incluyendo los ficticios añadidos)
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
                cost = next((e["cost"] for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                if cost is None:
                    messagebox.showerror("Error", f"Falta la arista de {s['id'][:4]} a {d['id'][:4]}.")
                    return
                c.append(cost)
                cost_terms.append(f"{cost}*x_{i + 1}{j + 1}")
        result_text += " + ".join(cost_terms) + "\n\n"

        # Restricciones de oferta (≤)
        result_text += "Restricciones de Oferta (≤):\n"
        for i in range(m):
            row = [0] * (m * n)
            for j in range(n):
                row[i * n + j] = 1
            A_ub.append(row)
            b_ub.append(supply_nodes[i]["supply"])
            terms = [f"x_{i + 1}{j + 1}" for j in range(n)]
            result_text += f"{' + '.join(terms)} ≤ {supply_nodes[i]['supply']} (Planta {supply_nodes[i]['id'][:4]})\n"

        # Restricciones de demanda (=)
        result_text += "\nRestricciones de Demanda (=):\n"
        for j in range(n):
            row = [0] * (m * n)
            for i in range(m):
                row[i * n + j] = 1
            A_eq.append(row)
            b_eq.append(demand_nodes[j]["demand"])
            terms = [f"x_{i + 1}{j + 1}" for i in range(m)]
            result_text += f"{' + '.join(terms)} = {demand_nodes[j]['demand']} (Comprador {demand_nodes[j]['id'][:4]})\n"

        # Restricciones de no negatividad
        result_text += "\nRestricciones de No Negatividad:\n"
        result_text += ", ".join([f"x_{i + 1}{j + 1} ≥ 0" for i in range(m) for j in range(n)]) + "\n\n"

        # Resolver con linprog (simplex)
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="simplex")

        if res.success:
            solution = res.x.reshape(m, n)
            result_text += "Solución Óptima (Transporte):\n"
            total_cost = 0
            used_fictitious = False
            for i, s in enumerate(supply_nodes):
                for j, d in enumerate(demand_nodes):
                    qty = solution[i][j]
                    if qty > 0:
                        cost = c[i * n + j]
                        result_text += f"De {s['id'][:4]} → {d['id'][:4]}: {qty} unidades, costo {cost * qty}\n"
                        total_cost += cost * qty
                        edge = next((e for e in self.edges if e["from"] == s["id"] and e["to"] == d["id"]), None)
                        if edge and edge.get("line_id") is not None:
                            self.canvas.itemconfig(edge["line_id"], fill="#4CAF50", width=3)
                            self.solution_edges.append(edge)
                        # Si alguno es ficticio, marcar nota
                        if s.get("fictitious", False) or d.get("fictitious", False):
                            used_fictitious = True
            result_text += f"Costo Total: {total_cost}\n"
            if used_fictitious:
                result_text += "\nNota: Se usaron nodos ficticios, lo que indica que el modelo no estaba balanceado originalmente."
            messagebox.showinfo("Resultado Transporte", result_text)
        else:
            messagebox.showerror("Error", "No se encontró solución óptima para transporte.")


if __name__ == "__main__":
    root = tk.Tk()
    app = TransportProblemGUI(root)
    root.mainloop()
