import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import urllib.request
import io
import os
import random
import threading
import queue
from movie import Movie, MovieManager


class ImageLoader:
    """Async image loader with memory cache."""
    _cache = {}
    _queue = queue.Queue()
    _worker_started = False

    @classmethod
    def start_worker(cls):
        if not cls._worker_started:
            cls._worker_started = True
            threading.Thread(target=cls._worker_loop, daemon=True).start()

    @classmethod
    def _worker_loop(cls):
        UA_HEADERS = {"User-Agent": "MovieManager/1.0"}
        while True:
            url, size, name, callback = cls._queue.get()
            try:
                if url in cls._cache:
                    img = cls._cache[url].resize(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    cls._queue.task_done()
                    cls._run_callback(callback, photo)
                    continue

                req = urllib.request.Request(url, headers=UA_HEADERS)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
                cls._cache[url] = img
                img = img.resize(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                cls._run_callback(callback, photo)
            except Exception:
                cls._run_callback(callback, None)
            finally:
                cls._queue.task_done()

    @classmethod
    def _run_callback(cls, callback, photo):
        try:
            callback(photo)
        except Exception:
            pass

    @classmethod
    def load(cls, url, size, name, callback):
        """Queue an image load; callback(photo) called on UI thread when ready."""
        if not url:
            callback(None)
            return
        cls._queue.put((url, size, name, callback))

    @classmethod
    def get_cached(cls, url, size):
        if url in cls._cache:
            return ImageTk.PhotoImage(cls._cache[url].resize(size, Image.Resampling.LANCZOS))
        return None


class COLORS:
    """Color palette for the application."""
    BG_PRIMARY = "#FFFFFF"
    BG_SECONDARY = "#F8F0F0"
    BG_CARD = "#FFFFFF"
    BG_ACCENT = "#FFF0F0"
    TEXT_PRIMARY = "#1A1A1A"
    TEXT_SECONDARY = "#6B3A3A"
    TEXT_LIGHT = "#C8A0A0"
    ACCENT = "#D7263D"
    ACCENT_HOVER = "#B51D30"
    SUCCESS = "#C81D2F"
    WARNING = "#E87D1E"
    DANGER = "#A51D2D"
    BORDER = "#E8D0D0"
    STAR = "#D7263D"


class MovieApp:
    """Main application class for the Movie Manager GUI."""

    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Personal Movie Manager")
        self.root.geometry("1200x750")
        self.root.configure(bg=COLORS.BG_PRIMARY)
        self.root.minsize(1000, 600)

        self.manager = MovieManager()
        self.current_image_refs = []

        ImageLoader.start_worker()

        self.setup_styles()
        self.create_widgets()
        self.load_movie_list()

    def setup_styles(self):
        """Configure ttk styles for the application."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Title.TLabel',
                       background=COLORS.BG_PRIMARY,
                       foreground=COLORS.TEXT_PRIMARY,
                       font=('Segoe UI', 24, 'bold'))

        style.configure('Subtitle.TLabel',
                       background=COLORS.BG_PRIMARY,
                       foreground=COLORS.TEXT_SECONDARY,
                       font=('Segoe UI', 11))

        style.configure('Card.TFrame',
                       background=COLORS.BG_CARD,
                       relief='flat')

        style.configure('Accent.TButton',
                       background=COLORS.ACCENT,
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))

        style.map('Accent.TButton',
                 background=[('active', COLORS.ACCENT_HOVER)])

        style.configure('Treeview',
                       background=COLORS.BG_CARD,
                       foreground=COLORS.TEXT_PRIMARY,
                       fieldbackground=COLORS.BG_CARD,
                       font=('Segoe UI', 10),
                       rowheight=35)

        style.configure('Treeview.Heading',
                       background=COLORS.BG_SECONDARY,
                       foreground=COLORS.TEXT_PRIMARY,
                       font=('Segoe UI', 10, 'bold'))

        style.map('Treeview',
                 background=[('selected', COLORS.BG_ACCENT)],
                 foreground=[('selected', COLORS.TEXT_PRIMARY)])

    def create_widgets(self):
        """Create and layout all GUI widgets."""
        main_container = tk.Frame(self.root, bg=COLORS.BG_PRIMARY)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        self.create_header(main_container)

        content_frame = tk.Frame(main_container, bg=COLORS.BG_PRIMARY)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        left_panel = tk.Frame(content_frame, bg=COLORS.BG_PRIMARY)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_panel = tk.Frame(content_frame, bg=COLORS.BG_PRIMARY, width=420)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        right_panel.pack_propagate(False)

        self.create_toolbar(left_panel)
        self.create_movie_list(left_panel)
        self.create_detail_panel(right_panel)

    def create_header(self, parent):
        """Create the application header."""
        header = tk.Frame(parent, bg=COLORS.BG_PRIMARY)
        header.pack(fill=tk.X)

        title_frame = tk.Frame(header, bg=COLORS.BG_PRIMARY)
        title_frame.pack(side=tk.LEFT)

        ttk.Label(title_frame, text="🎬 Personal Movie Manager",
                 style='Title.TLabel').pack(anchor='w')
        ttk.Label(title_frame, text="Organize and discover your favorite films",
                 style='Subtitle.TLabel').pack(anchor='w', pady=(2, 0))

        btn_frame = tk.Frame(header, bg=COLORS.BG_PRIMARY)
        btn_frame.pack(side=tk.RIGHT, pady=10)

        self.create_styled_button(btn_frame, "+ Add Movie",
                                  self.add_movie_dialog, COLORS.SUCCESS)

        stats_frame = tk.Frame(header, bg=COLORS.BG_ACCENT, padx=15, pady=8)
        stats_frame.pack(side=tk.RIGHT, padx=(0, 15))
        self.stats_label = tk.Label(stats_frame,
                                   text=f"Movies: {self.manager.count}",
                                   bg=COLORS.BG_ACCENT,
                                   fg=COLORS.TEXT_PRIMARY,
                                   font=('Segoe UI', 11, 'bold'))
        self.stats_label.pack()

    def create_styled_button(self, parent, text, command, color=None):
        """Create a styled button."""
        bg = color or COLORS.ACCENT
        btn = tk.Button(parent, text=text, command=command,
                       bg=bg, fg='white',
                       font=('Segoe UI', 10, 'bold'),
                       relief='flat', padx=15, pady=6,
                       cursor='hand2', activebackground=COLORS.ACCENT_HOVER)
        btn.pack(side=tk.LEFT, padx=3)
        return btn

    def create_toolbar(self, parent):
        """Create search and filter toolbar."""
        toolbar = tk.Frame(parent, bg=COLORS.BG_CARD, padx=10, pady=10,
                          highlightbackground=COLORS.BORDER,
                          highlightthickness=1)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        search_frame = tk.Frame(toolbar, bg=COLORS.BG_CARD)
        search_frame.pack(fill=tk.X)

        tk.Label(search_frame, text="🔍", bg=COLORS.BG_CARD,
                font=('Segoe UI', 12)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_movies())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=('Segoe UI', 11),
                               bg=COLORS.BG_SECONDARY,
                               relief='flat', width=35)
        search_entry.pack(side=tk.LEFT, padx=8, ipady=4)

        self.create_styled_button(search_frame, "Clear",
                                  lambda: self.search_var.set(""),
                                  COLORS.TEXT_SECONDARY)

        sort_frame = tk.Frame(toolbar, bg=COLORS.BG_CARD)
        sort_frame.pack(fill=tk.X, pady=(8, 0))

        tk.Label(sort_frame, text="Sort by:", bg=COLORS.BG_CARD,
                font=('Segoe UI', 10)).pack(side=tk.LEFT)

        sort_options = ["Name", "IMDb Rating", "Director", "Cast", "Year"]
        self.sort_var = tk.StringVar(value="Name")
        sort_menu = tk.OptionMenu(sort_frame, self.sort_var, *sort_options,
                                  command=lambda *args: self.sort_movies())
        sort_menu.configure(font=('Segoe UI', 10), bg=COLORS.BG_SECONDARY,
                           relief='flat')
        sort_menu['menu'].configure(font=('Segoe UI', 10))
        sort_menu.pack(side=tk.LEFT, padx=8)

        self.create_styled_button(sort_frame, "Refresh",
                                  self.load_movie_list, COLORS.ACCENT)

    def create_movie_list(self, parent):
        """Create the movie list with Treeview."""
        list_frame = tk.Frame(parent, bg=COLORS.BG_CARD,
                             highlightbackground=COLORS.BORDER,
                             highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Title", "Director", "Year", "IMDb", "Genre")
        self.tree = ttk.Treeview(list_frame, columns=columns,
                                show='headings', selectmode='browse')

        self.tree.heading("Title", text="Title", anchor='w')
        self.tree.heading("Director", text="Director")
        self.tree.heading("Year", text="Year")
        self.tree.heading("IMDb", text="IMDb")
        self.tree.heading("Genre", text="Genre")

        self.tree.column("Title", width=250, minwidth=150)
        self.tree.column("Director", width=150, minwidth=100)
        self.tree.column("Year", width=70, minwidth=50)
        self.tree.column("IMDb", width=70, minwidth=50)
        self.tree.column("Genre", width=120, minwidth=80)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                 command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_movie_select)
        self.tree.bind('<Double-1>', lambda e: self.view_movie_detail())

        btn_frame = tk.Frame(parent, bg=COLORS.BG_PRIMARY)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        self.create_styled_button(btn_frame, "View Details",
                                  self.view_movie_detail, COLORS.ACCENT)
        self.create_styled_button(btn_frame, "Edit",
                                  self.edit_movie_dialog, COLORS.WARNING)
        self.create_styled_button(btn_frame, "Delete",
                                  self.delete_movie, COLORS.DANGER)

    def create_detail_panel(self, parent):
        """Create the movie detail panel."""
        self.detail_canvas = tk.Canvas(parent, bg=COLORS.BG_CARD,
                                       highlightthickness=0)
        detail_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL,
                                         command=self.detail_canvas.yview)
        self.detail_inner = tk.Frame(self.detail_canvas, bg=COLORS.BG_CARD,
                                     padx=15, pady=15)

        self.detail_inner.bind("<Configure>",
                              lambda e: self.detail_canvas.configure(
                                  scrollregion=self.detail_canvas.bbox("all")))

        self.detail_canvas.create_window((0, 0), window=self.detail_inner,
                                        anchor='nw')
        self.detail_canvas.configure(yscrollcommand=detail_scrollbar.set)

        self.detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.detail_title = tk.Label(self.detail_inner,
                                    text="Select a movie to view details",
                                    bg=COLORS.BG_CARD,
                                    fg=COLORS.TEXT_PRIMARY,
                                    font=('Segoe UI', 20, 'bold'),
                                    wraplength=380, justify='left')
        self.detail_title.pack(anchor='w', pady=(0, 5))

        self.detail_meta = tk.Label(self.detail_inner,
                                   text="",
                                   bg=COLORS.BG_CARD,
                                   fg=COLORS.TEXT_SECONDARY,
                                   font=('Segoe UI', 10),
                                   wraplength=380, justify='left')
        self.detail_meta.pack(anchor='w', pady=(0, 10))

        self.detail_imdb = tk.Label(self.detail_inner,
                                   text="",
                                   bg=COLORS.STAR,
                                   fg='white',
                                   font=('Segoe UI', 12, 'bold'),
                                   padx=10, pady=3)
        self.detail_imdb.pack(anchor='w', pady=(0, 10))

        self.detail_poster_label = tk.Label(self.detail_inner,
                                           bg=COLORS.BG_CARD)
        self.detail_poster_label.pack(anchor='w', pady=(0, 10))

        self.detail_desc = tk.Label(self.detail_inner,
                                   text="",
                                   bg=COLORS.BG_CARD,
                                   fg=COLORS.TEXT_PRIMARY,
                                   font=('Segoe UI', 10),
                                   wraplength=380, justify='left')
        self.detail_desc.pack(anchor='w', pady=(0, 10))

        self.director_frame = tk.Frame(self.detail_inner, bg=COLORS.BG_ACCENT,
                                       padx=10, pady=8)
        self.director_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(self.director_frame, text="🎬 Director",
                bg=COLORS.BG_ACCENT, fg=COLORS.ACCENT,
                font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        self.director_info_frame = tk.Frame(self.director_frame,
                                           bg=COLORS.BG_ACCENT)
        self.director_info_frame.pack(fill=tk.X, pady=(5, 0))

        self.director_img_label = tk.Label(self.director_info_frame,
                                          bg=COLORS.BG_ACCENT)
        self.director_img_label.pack(side=tk.LEFT, padx=(0, 10))

        self.director_bio_label = tk.Label(self.director_info_frame,
                                          text="",
                                          bg=COLORS.BG_ACCENT,
                                          fg=COLORS.TEXT_PRIMARY,
                                          font=('Segoe UI', 9),
                                          wraplength=260, justify='left')
        self.director_bio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.cast_frame = tk.Frame(self.detail_inner, bg=COLORS.BG_ACCENT,
                                   padx=10, pady=8)
        self.cast_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(self.cast_frame, text="🎭 Cast",
                bg=COLORS.BG_ACCENT, fg=COLORS.ACCENT,
                font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        self.cast_info_frame = tk.Frame(self.cast_frame, bg=COLORS.BG_ACCENT)
        self.cast_info_frame.pack(fill=tk.X, pady=(5, 0))

        self.cast_img_frame = tk.Frame(self.cast_info_frame,
                                       bg=COLORS.BG_ACCENT)
        self.cast_img_frame.pack(anchor='w')

        self.cast_bio_label = tk.Label(self.cast_info_frame,
                                      text="",
                                      bg=COLORS.BG_ACCENT,
                                      fg=COLORS.TEXT_PRIMARY,
                                      font=('Segoe UI', 9),
                                      wraplength=380, justify='left')
        self.cast_bio_label.pack(anchor='w', pady=(5, 0))

    def load_movie_list(self):
        """Load all movies into the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for movie in self.manager.movies:
            self.tree.insert('', 'end', values=(
                movie.title,
                movie.director,
                movie.year or "N/A",
                movie.imdb_rating or "N/A",
                movie.genre or "N/A"
            ))

        self.stats_label.config(text=f"Movies: {self.manager.count}")

    def search_movies(self):
        """Search and filter movies."""
        query = self.search_var.get()
        results = self.manager.search_movies(query)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for movie in results:
            self.tree.insert('', 'end', values=(
                movie.title,
                movie.director,
                movie.year or "N/A",
                movie.imdb_rating or "N/A",
                movie.genre or "N/A"
            ))

    def sort_movies(self):
        """Sort movies based on selected option."""
        sort_by = self.sort_var.get()

        if sort_by == "IMDb Rating":
            sorted_movies = self.manager.get_sorted_by_imdb()
        elif sort_by == "Director":
            sorted_movies = self.manager.get_sorted_by_director()
        elif sort_by == "Cast":
            sorted_movies = self.manager.get_sorted_by_cast()
        elif sort_by == "Year":
            sorted_movies = sorted(self.manager.movies,
                                  key=lambda m: m.year or "0000", reverse=True)
        else:
            sorted_movies = sorted(self.manager.movies,
                                  key=lambda m: m.title.lower())

        for item in self.tree.get_children():
            self.tree.delete(item)

        for movie in sorted_movies:
            self.tree.insert('', 'end', values=(
                movie.title,
                movie.director,
                movie.year or "N/A",
                movie.imdb_rating or "N/A",
                movie.genre or "N/A"
            ))

    def on_movie_select(self, event):
        """Handle movie selection in the treeview."""
        self.view_movie_detail()

    def get_selected_movie_index(self):
        """Get the index of the selected movie."""
        selection = self.tree.selection()
        if not selection:
            return None
        item = self.tree.item(selection[0])
        title = item['values'][0]
        for i, movie in enumerate(self.manager.movies):
            if movie.title == title:
                return i
        return None

    def view_movie_detail(self):
        """Display detailed information for selected movie."""
        idx = self.get_selected_movie_index()
        if idx is None:
            return

        movie = self.manager.movies[idx]

        self.detail_title.config(text=movie.title)

        meta_parts = []
        if movie.year:
            meta_parts.append(f"📅 {movie.year}")
        if movie.genre:
            meta_parts.append(f"🏷 {movie.genre}")
        self.detail_meta.config(text="  |  ".join(meta_parts) if meta_parts else "")

        if movie.imdb_rating:
            self.detail_imdb.config(text=f"⭐ IMDb: {movie.imdb_rating}/10")
            self.detail_imdb.pack(anchor='w', pady=(0, 10))
        else:
            self.detail_imdb.pack_forget()

        self._clear_label(self.detail_poster_label)
        self._load_image_async(movie.poster, self.detail_poster_label, (200, 300), movie.title)

        if movie.description:
            self.detail_desc.config(text=f"📝 {movie.description}")
            self.detail_desc.pack(anchor='w', pady=(0, 10))
        else:
            self.detail_desc.pack_forget()

        if movie.director:
            director_text = movie.director
            if movie.director_bio:
                director_text += f"\n\n{movie.director_bio}"
            self.director_bio_label.config(text=director_text)
            self._clear_label(self.director_img_label)
            self._load_image_async(movie.director_image, self.director_img_label,
                                  (60, 60), movie.director)
            self.director_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.director_frame.pack_forget()

        if movie.cast:
            cast_names = ", ".join(movie.cast)
            cast_text = f"Cast: {cast_names}"
            if movie.cast_bio:
                cast_text += f"\n\n{movie.cast_bio}"
            self.cast_bio_label.config(text=cast_text)

            for widget in self.cast_img_frame.winfo_children():
                widget.destroy()

            for i, img_url in enumerate(movie.cast_images[:5]):
                img_label = tk.Label(self.cast_img_frame, bg=COLORS.BG_ACCENT)
                img_label.pack(side=tk.LEFT, padx=2)
                cast_name = movie.cast[i] if i < len(movie.cast) else ""
                self._load_image_async(img_url, img_label, (50, 50), cast_name)

            self.cast_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.cast_frame.pack_forget()

    def _clear_label(self, label):
        """Clear a label's image."""
        label.config(image="", text="")
        label.image = None

    def _load_image_async(self, url, label, size, name=""):
        """Load image asynchronously; show initials immediately, swap when ready."""
        if not url:
            self._show_initials(label, size, name or "?")
            return

        # Check memory cache first for instant display
        cached = ImageLoader.get_cached(url, size)
        if cached:
            label.config(image=cached, text="")
            label.image = cached
            self.current_image_refs.append(cached)
            return

        # Show initials placeholder immediately
        self._show_initials(label, size, name)

        # Queue async load
        def on_loaded(photo):
            def apply():
                if label.winfo_exists():
                    label.config(image=photo, text="")
                    label.image = photo
                    self.current_image_refs.append(photo)
            self.root.after(0, apply)

        ImageLoader.load(url, size, name, on_loaded)

    def _show_initials(self, label, size, name):
        """Draw a colored avatar with the person's initials."""
        try:
            w, h = size
            colors = ["#D7263D", "#B51D30", "#C81D2F", "#E87D1E",
                      "#A51D2D", "#E0A0A0", "#D08080", "#C06060"]
            bg = colors[random.randrange(len(colors))]

            img = Image.new("RGB", (w, h), bg)
            draw = ImageDraw.Draw(img)

            initials = ""
            for part in name.split()[:2]:
                if part:
                    initials += part[0].upper()

            try:
                font = ImageFont.truetype("arial.ttf", int(h * 0.4))
            except IOError:
                font = ImageFont.load_default()

            if font:
                bbox = draw.textbbox((0, 0), initials, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                tw = th = h // 2

            x = (w - tw) // 2 - bbox[0]
            y = (h - th) // 2 - bbox[1]
            draw.text((x, y), initials, fill="white", font=font)

            photo = ImageTk.PhotoImage(img)
            label.config(image=photo, text="")
            label.image = photo
            self.current_image_refs.append(photo)
        except Exception:
            label.config(text="[No Image]")

    def add_movie_dialog(self):
        """Open dialog to add a new movie."""
        dialog = MovieDialog(self.root, "Add New Movie")
        if dialog.result:
            movie = Movie(**dialog.result)
            if self.manager.add_movie(movie):
                self.load_movie_list()
                messagebox.showinfo("Success", "Movie added successfully!")
            else:
                messagebox.showerror("Error", "Failed to add movie.")

    def edit_movie_dialog(self):
        """Open dialog to edit selected movie."""
        idx = self.get_selected_movie_index()
        if idx is None:
            messagebox.showwarning("Warning", "Please select a movie to edit.")
            return

        movie = self.manager.movies[idx]
        dialog = MovieDialog(self.root, "Edit Movie", movie.to_dict())

        if dialog.result:
            updated_movie = Movie(**dialog.result)
            if self.manager.update_movie(idx, updated_movie):
                self.load_movie_list()
                messagebox.showinfo("Success", "Movie updated successfully!")
            else:
                messagebox.showerror("Error", "Failed to update movie.")

    def delete_movie(self):
        """Delete selected movie after confirmation."""
        idx = self.get_selected_movie_index()
        if idx is None:
            messagebox.showwarning("Warning", "Please select a movie to delete.")
            return

        movie = self.manager.movies[idx]
        if messagebox.askyesno("Confirm Delete",
                              f"Delete '{movie.title}'?"):
            if self.manager.remove_movie(idx):
                self.load_movie_list()
                self.clear_detail_panel()
                messagebox.showinfo("Success", "Movie deleted successfully!")
            else:
                messagebox.showerror("Error", "Failed to delete movie.")

    def clear_detail_panel(self):
        """Clear the detail panel."""
        self.detail_title.config(text="Select a movie to view details")
        self.detail_meta.config(text="")
        self.detail_imdb.pack_forget()
        self.detail_poster_label.config(image="")
        self.detail_desc.config(text="")
        self.director_frame.pack_forget()
        self.cast_frame.pack_forget()


class MovieDialog:
    """Dialog for adding/editing movies."""

    def __init__(self, parent, title, movie_data=None):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x650")
        self.dialog.configure(bg=COLORS.BG_PRIMARY)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.geometry("+%d+%d" %
                           (parent.winfo_rootx() + 50,
                            parent.winfo_rooty() + 50))

        main_frame = tk.Frame(self.dialog, bg=COLORS.BG_PRIMARY, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text=title,
                bg=COLORS.BG_PRIMARY, fg=COLORS.TEXT_PRIMARY,
                font=('Segoe UI', 16, 'bold')).pack(anchor='w', pady=(0, 15))

        canvas = tk.Canvas(main_frame, bg=COLORS.BG_PRIMARY,
                          highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL,
                                 command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS.BG_PRIMARY)

        scroll_frame.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        self.fields = {}
        field_config = [
            ("title", "Movie Title *", True),
            ("director", "Director *", True),
            ("cast", "Cast (comma-separated) *", True),
            ("year", "Year", False),
            ("genre", "Genre", False),
            ("imdb_rating", "IMDb Rating (0-10)", False),
            ("description", "Description", False),
            ("poster", "Poster URL", False),
            ("director_image", "Director Image URL", False),
            ("cast_images", "Cast Image URLs (comma-separated)", False),
            ("director_bio", "Director Biography", False),
            ("cast_bio", "Cast Biography", False),
        ]

        for field_id, label, required in field_config:
            frame = tk.Frame(scroll_frame, bg=COLORS.BG_PRIMARY)
            frame.pack(fill=tk.X, pady=(0, 10))

            lbl_text = label + (" *" if required else "")
            tk.Label(frame, text=lbl_text, bg=COLORS.BG_PRIMARY,
                    fg=COLORS.TEXT_PRIMARY,
                    font=('Segoe UI', 10, 'bold')).pack(anchor='w')

            if field_id in ("description", "director_bio", "cast_bio"):
                entry = tk.Text(frame, font=('Segoe UI', 10),
                               bg=COLORS.BG_SECONDARY, relief='flat',
                               height=3, width=45)
                entry.pack(fill=tk.X, pady=(3, 0), ipady=4)
            else:
                entry = tk.Entry(frame, font=('Segoe UI', 10),
                                bg=COLORS.BG_SECONDARY, relief='flat')
                entry.pack(fill=tk.X, pady=(3, 0), ipady=4)

            self.fields[field_id] = entry

        if movie_data:
            for field_id, entry in self.fields.items():
                value = movie_data.get(field_id, "")
                if isinstance(value, list):
                    value = ", ".join(value)
                if isinstance(entry, tk.Text):
                    entry.insert('1.0', str(value))
                else:
                    entry.insert(0, str(value))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(main_frame, bg=COLORS.BG_PRIMARY)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        tk.Button(btn_frame, text="Cancel", command=self.dialog.destroy,
                 bg=COLORS.TEXT_SECONDARY, fg='white',
                 font=('Segoe UI', 10, 'bold'), relief='flat',
                 padx=20, pady=6, cursor='hand2').pack(side=tk.LEFT)

        tk.Button(btn_frame, text="Save", command=self.save,
                 bg=COLORS.SUCCESS, fg='white',
                 font=('Segoe UI', 10, 'bold'), relief='flat',
                 padx=20, pady=6, cursor='hand2').pack(side=tk.RIGHT)

        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def save(self):
        """Validate and save the form data."""
        title = self.fields["title"].get().strip()
        director = self.fields["director"].get().strip()
        cast_str = self.fields["cast"].get().strip()

        if not all([title, director, cast_str]):
            messagebox.showwarning("Validation Error",
                                 "Title, Director, and Cast are required.",
                                 parent=self.dialog)
            return

        try:
            imdb = float(self.fields["imdb_rating"].get().strip() or 0)
            if not (0 <= imdb <= 10):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation Error",
                                 "IMDb rating must be a number between 0 and 10.",
                                 parent=self.dialog)
            return

        cast_list = [c.strip() for c in cast_str.split(",") if c.strip()]

        cast_images_str = self.fields["cast_images"].get().strip()
        cast_images = [u.strip() for u in cast_images_str.split(",") if u.strip()]

        self.result = {
            "title": title,
            "director": director,
            "cast": cast_list,
            "year": self.fields["year"].get().strip(),
            "genre": self.fields["genre"].get().strip(),
            "imdb_rating": imdb,
            "description": self.fields["description"].get("1.0", "end-1c").strip(),
            "poster": self.fields["poster"].get().strip(),
            "director_image": self.fields["director_image"].get().strip(),
            "cast_images": cast_images,
            "director_bio": self.fields["director_bio"].get("1.0", "end-1c").strip(),
            "cast_bio": self.fields["cast_bio"].get("1.0", "end-1c").strip(),
        }

        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = MovieApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
