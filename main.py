from __future__ import annotations

from dataclasses import dataclass
from tkinter import colorchooser
import tkinter as tk


@dataclass
class Point:
    x: float
    y: float
    handle_dx: float = 0.0
    handle_dy: float = 0.0
    custom_handle: bool = False


class CurveEditor(tk.Tk):
    canvas_width = 960
    canvas_height = 640
    point_radius = 6
    handle_radius = 8
    handle_hit_radius = 18
    hit_radius = 12
    curve_width = 3
    handle_width = 2
    handle_length_scale = 0.35
    handle_length_min = 32.0
    handle_length_max = 72.0
    steps_per_segment = 28

    def __init__(self) -> None:
        super().__init__()
        self.title("Curve Editor")
        self.geometry("1120x760")
        self.minsize(720, 480)
        self.configure(bg="#ececec")

        self.points: list[Point] = []
        self.selected_index: int | None = None
        self.drag_mode: str | None = None
        self.drag_handle_side: int | None = None
        self.draw_enabled = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.curve_color = "#1f4b99"
        self.draw_toggle: tk.Checkbutton | None = None
        self.points_toggle: tk.Checkbutton | None = None
        self.color_button: tk.Button | None = None
        self.color_preview: tk.Label | None = None
        self.mode_text: tk.Label | None = None

        self._build_ui()
        self._bind_events()
        self.after_idle(self.redraw)

    def _build_ui(self) -> None:
        toolbar = tk.Frame(self, bg="#ececec", highlightthickness=0)
        toolbar.pack(side="top", fill="x", padx=12, pady=(12, 8))

        tk.Button(
            toolbar,
            text="Undo",
            command=self.undo_point,
            width=8,
            relief="flat",
        ).pack(side="left")

        tk.Button(
            toolbar,
            text="Clear",
            command=self.clear_points,
            width=8,
            relief="flat",
        ).pack(side="left", padx=(8, 0))

        self.draw_toggle = tk.Checkbutton(
            toolbar,
            text="绘画模式",
            variable=self.draw_enabled,
            indicatoron=False,
            relief="flat",
            width=10,
            padx=8,
            pady=3,
            command=self._update_mode_text,
        )
        self.draw_toggle.pack(side="left", padx=(8, 0))

        self.points_toggle = tk.Checkbutton(
            toolbar,
            text="显示点",
            variable=self.show_points,
            indicatoron=False,
            relief="flat",
            width=8,
            padx=8,
            pady=3,
            command=self.redraw,
        )
        self.points_toggle.pack(side="left", padx=(8, 0))

        self.color_button = tk.Button(
            toolbar,
            text="曲线颜色",
            command=self.choose_curve_color,
            width=10,
            relief="flat",
        )
        self.color_button.pack(side="left", padx=(8, 0))

        self.color_preview = tk.Label(
            toolbar,
            text=self.curve_color.upper(),
            bg=self.curve_color,
            fg="#ffffff",
            width=10,
            relief="solid",
            bd=1,
        )
        self.color_preview.pack(side="left", padx=(6, 0))

        self.mode_text = tk.Label(
            toolbar,
            text="当前：绘画开启",
            bg="#ececec",
            fg="#0f766e",
            anchor="w",
            justify="left",
        )
        self.mode_text.pack(side="left", padx=(10, 0))

        self.canvas = tk.Canvas(
            self,
            bg="#ffffff",
            highlightthickness=0,
            width=self.canvas_width,
            height=self.canvas_height,
        )
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _bind_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.bind("<Control-z>", lambda event: self.undo_point())
        self.bind("<Escape>", lambda event: self.clear_points())
        self.bind("<BackSpace>", lambda event: self.undo_point())

    def _update_mode_text(self) -> None:
        if self.mode_text is None:
            return

        if self.draw_enabled.get():
            self.mode_text.config(text="当前：绘画开启", fg="#0f766e")
        else:
            self.mode_text.config(text="当前：绘画关闭", fg="#b45309")

    def choose_curve_color(self) -> None:
        _, selected_color = colorchooser.askcolor(
            title="选择曲线颜色",
            color=self.curve_color,
        )
        if not selected_color:
            return

        self.curve_color = selected_color
        self._update_curve_color_preview()
        self.redraw()

    def _update_curve_color_preview(self) -> None:
        if self.color_preview is None:
            return

        self.color_preview.config(text=self.curve_color.upper(), bg=self.curve_color)
        self.color_preview.config(fg=self._contrast_text_color(self.curve_color))

    def on_left_press(self, event: tk.Event) -> None:
        handle_hit = self._selected_handle_endpoint(event.x, event.y)
        if handle_hit is not None:
            handle_index, handle_side = handle_hit
            self.selected_index = handle_index
            self.drag_mode = "handle"
            self.drag_handle_side = handle_side
            self.redraw()
            return

        index = self._nearest_point_index(event.x, event.y)
        if index is None:
            if not self.draw_enabled.get():
                self.selected_index = None
                self.drag_mode = None
                self.drag_handle_side = None
                self.redraw()
                return

            self.add_point(event.x, event.y, select=False)
            return

        self.selected_index = index
        self.drag_mode = "point"
        self.drag_handle_side = None
        self.redraw()

    def on_left_drag(self, event: tk.Event) -> None:
        if self.selected_index is None or self.drag_mode is None:
            return

        point = self.points[self.selected_index]
        if self.drag_mode == "point":
            point.x = self._clamp(event.x, 0, max(1, self.canvas.winfo_width() - 1))
            point.y = self._clamp(event.y, 0, max(1, self.canvas.winfo_height() - 1))
        elif self.drag_mode == "handle":
            handle_side = self.drag_handle_side or 1
            offset_x = event.x - point.x
            offset_y = event.y - point.y
            if handle_side < 0:
                offset_x = -offset_x
                offset_y = -offset_y

            point.handle_dx = offset_x
            point.handle_dy = offset_y
            point.custom_handle = True

        self.redraw()

    def on_left_release(self, event: tk.Event) -> None:
        self.drag_mode = None
        self.drag_handle_side = None

    def on_right_click(self, event: tk.Event) -> None:
        index = self._nearest_point_index(event.x, event.y)
        if index is None:
            return

        self.points.pop(index)
        if self.selected_index is not None:
            if index == self.selected_index:
                self.selected_index = None
            elif index < self.selected_index:
                self.selected_index -= 1

        self.drag_mode = None
        self.drag_handle_side = None
        self.redraw()

    def add_point(self, x: float, y: float, select: bool = False) -> None:
        self.points.append(Point(x, y))
        self.selected_index = len(self.points) - 1 if select else None
        self.drag_mode = None
        self.drag_handle_side = None
        self.redraw()

    def undo_point(self) -> None:
        if not self.points:
            return

        self.points.pop()
        self.selected_index = None
        self.drag_mode = None
        self.drag_handle_side = None
        self.redraw()

    def clear_points(self) -> None:
        if not self.points:
            return

        self.points.clear()
        self.selected_index = None
        self.drag_mode = None
        self.drag_handle_side = None
        self.redraw()

    def toggle_draw_mode(self) -> None:
        self._update_mode_text()

    def redraw(self) -> None:
        self.canvas.delete("all")

        if len(self.points) >= 2:
            polyline = self._build_curve_polyline(self.points)
            if len(polyline) >= 2:
                coords = [coordinate for point in polyline for coordinate in point]
                self.canvas.create_line(
                    *coords,
                    fill=self.curve_color,
                    width=self.curve_width,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                    smooth=False,
                )

        if self.show_points.get():
            for index, point in enumerate(self.points):
                self._draw_point(index, point)

        if self.selected_index is not None and 0 <= self.selected_index < len(self.points):
            self._draw_handle(self.selected_index)

    def _draw_point(self, index: int, point: Point) -> None:
        radius = self.point_radius
        is_selected = index == self.selected_index
        fill = "#111111" if is_selected else "#ffffff"
        outline = "#111111"
        self.canvas.create_oval(
            point.x - radius,
            point.y - radius,
            point.x + radius,
            point.y + radius,
            fill=fill,
            outline=outline,
            width=2,
        )

    def _draw_handle(self, index: int) -> None:
        point = self.points[index]
        left_handle, right_handle = self._handle_points(index)
        is_custom = point.custom_handle
        line_color = "#d97706" if is_custom else "#a16207"
        dash = () if is_custom else (5, 4)
        arrow_shape = (8, 10, 3)

        self.canvas.create_line(
            point.x,
            point.y,
            left_handle[0],
            left_handle[1],
            fill=line_color,
            width=self.handle_width,
            dash=dash,
            arrow=tk.LAST,
            arrowshape=arrow_shape,
        )
        self.canvas.create_line(
            point.x,
            point.y,
            right_handle[0],
            right_handle[1],
            fill=line_color,
            width=self.handle_width,
            dash=dash,
            arrow=tk.LAST,
            arrowshape=arrow_shape,
        )
        self.canvas.create_oval(
            left_handle[0] - self.handle_radius,
            left_handle[1] - self.handle_radius,
            left_handle[0] + self.handle_radius,
            left_handle[1] + self.handle_radius,
            fill="#ffffff",
            outline=line_color,
            width=2,
        )
        self.canvas.create_oval(
            right_handle[0] - self.handle_radius,
            right_handle[1] - self.handle_radius,
            right_handle[0] + self.handle_radius,
            right_handle[1] + self.handle_radius,
            fill="#ffffff",
            outline=line_color,
            width=2,
        )

    def _nearest_point_index(self, x: float, y: float) -> int | None:
        best_index: int | None = None
        best_distance = float(self.hit_radius * self.hit_radius)

        for index, point in enumerate(self.points):
            distance = self._distance_sq(point.x, point.y, x, y)
            if distance <= best_distance:
                best_distance = distance
                best_index = index

        return best_index

    def _handle_hit(self, index: int, x: float, y: float) -> bool:
        if self.selected_index != index:
            return False

        left_handle, right_handle = self._handle_points(index)
        hit_radius_sq = float(self.handle_hit_radius * self.handle_hit_radius)
        return (
            self._distance_sq(left_handle[0], left_handle[1], x, y) <= hit_radius_sq
            or self._distance_sq(right_handle[0], right_handle[1], x, y) <= hit_radius_sq
        )

    def _selected_handle_endpoint(self, x: float, y: float) -> tuple[int, int] | None:
        if self.selected_index is None:
            return None

        left_handle, right_handle = self._handle_points(self.selected_index)
        hit_radius_sq = float(self.handle_hit_radius * self.handle_hit_radius)

        if self._distance_sq(left_handle[0], left_handle[1], x, y) <= hit_radius_sq:
            return self.selected_index, -1

        if self._distance_sq(right_handle[0], right_handle[1], x, y) <= hit_radius_sq:
            return self.selected_index, 1

        return None

    def _handle_points(self, index: int) -> tuple[tuple[float, float], tuple[float, float]]:
        point = self.points[index]
        if point.custom_handle:
            offset_x = point.handle_dx
            offset_y = point.handle_dy
        else:
            offset_x, offset_y = self._auto_handle_offset(index)

        left_handle = (point.x - offset_x, point.y - offset_y)
        right_handle = (point.x + offset_x, point.y + offset_y)
        return left_handle, right_handle

    def _handle_end(self, index: int) -> tuple[float, float]:
        point = self.points[index]
        if point.custom_handle:
            return point.x + point.handle_dx, point.y + point.handle_dy

        offset_x, offset_y = self._auto_handle_offset(index)
        return point.x + offset_x, point.y + offset_y

    def _auto_handle_offset(self, index: int) -> tuple[float, float]:
        if len(self.points) < 2:
            return 0.0, 0.0

        if index <= 0:
            left = self.points[0]
            right = self.points[1]
            dx = right.x - left.x
            dy = right.y - left.y
        elif index >= len(self.points) - 1:
            left = self.points[-2]
            right = self.points[-1]
            dx = right.x - left.x
            dy = right.y - left.y
        else:
            left = self.points[index - 1]
            right = self.points[index + 1]
            dx = right.x - left.x
            dy = right.y - left.y

        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return 0.0, 0.0

        handle_length = self._clamp(
            length * self.handle_length_scale,
            self.handle_length_min,
            self.handle_length_max,
        )
        scale = handle_length / length
        return dx * scale, dy * scale

    def _build_curve_polyline(self, points: list[Point]) -> list[tuple[float, float]]:
        if len(points) < 2:
            return []

        polyline: list[tuple[float, float]] = []
        for index in range(len(points) - 1):
            start = points[index]
            end = points[index + 1]
            control1 = self._handle_end(index)
            end_handle_x, end_handle_y = self._handle_end(index + 1)
            control2 = (
                2 * end.x - end_handle_x,
                2 * end.y - end_handle_y,
            )

            segment = self._sample_cubic_bezier(
                (start.x, start.y),
                control1,
                control2,
                (end.x, end.y),
            )
            if polyline:
                segment = segment[1:]
            polyline.extend(segment)

        return polyline

    def _sample_cubic_bezier(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
    ) -> list[tuple[float, float]]:
        samples: list[tuple[float, float]] = []
        for step in range(self.steps_per_segment + 1):
            t = step / self.steps_per_segment
            omt = 1.0 - t
            omt2 = omt * omt
            t2 = t * t
            x = (
                omt2 * omt * p0[0]
                + 3 * omt2 * t * p1[0]
                + 3 * omt * t2 * p2[0]
                + t2 * t * p3[0]
            )
            y = (
                omt2 * omt * p0[1]
                + 3 * omt2 * t * p1[1]
                + 3 * omt * t2 * p2[1]
                + t2 * t * p3[1]
            )
            samples.append((x, y))

        return samples

    @staticmethod
    def _distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(value, maximum))

    @staticmethod
    def _contrast_text_color(hex_color: str) -> str:
        color = hex_color.lstrip("#")
        if len(color) != 6:
            return "#ffffff"

        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        return "#111111" if brightness > 160 else "#ffffff"


def main() -> None:
    app = CurveEditor()
    app.mainloop()


if __name__ == "__main__":
    main()