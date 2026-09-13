import json
import os
from datetime import datetime


class Movie:
    """Represents a single movie with all its information."""

    def __init__(self, title, director, cast, description, imdb_rating,
                 director_bio="", cast_bio="", director_image="", cast_images=None,
                 poster="", year="", genre=""):
        self.title = title
        self.director = director
        self.cast = cast if isinstance(cast, list) else [cast]
        self.description = description
        self.imdb_rating = imdb_rating
        self.director_bio = director_bio
        self.cast_bio = cast_bio
        self.director_image = director_image
        self.cast_images = cast_images if cast_images else []
        self.poster = poster
        self.year = year
        self.genre = genre
        self.date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        """Convert movie object to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "director": self.director,
            "cast": self.cast,
            "description": self.description,
            "imdb_rating": self.imdb_rating,
            "director_bio": self.director_bio,
            "cast_bio": self.cast_bio,
            "director_image": self.director_image,
            "cast_images": self.cast_images,
            "poster": self.poster,
            "year": self.year,
            "genre": self.genre,
            "date_added": self.date_added
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Movie object from a dictionary."""
        return cls(
            title=data.get("title", ""),
            director=data.get("director", ""),
            cast=data.get("cast", []),
            description=data.get("description", ""),
            imdb_rating=data.get("imdb_rating", 0.0),
            director_bio=data.get("director_bio", ""),
            cast_bio=data.get("cast_bio", ""),
            director_image=data.get("director_image", ""),
            cast_images=data.get("cast_images", []),
            poster=data.get("poster", ""),
            year=data.get("year", ""),
            genre=data.get("genre", "")
        )

    def __str__(self):
        return f"{self.title} ({self.year}) - Dir: {self.director} - IMDb: {self.imdb_rating}"


class MovieManager:
    """Manages the collection of movies with JSON persistence."""

    def __init__(self, filepath="movies.json"):
        self.filepath = filepath
        self.movies = []
        self.load_movies()

    def load_movies(self):
        """Load movies from JSON file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.movies = [Movie.from_dict(m) for m in data]
            else:
                self.movies = []
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Error loading movies: {e}")
            self.movies = []

    def save_movies(self):
        """Save movies to JSON file."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump([m.to_dict() for m in self.movies], f, indent=4,
                          ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving movies: {e}")
            return False

    def add_movie(self, movie):
        """Add a new movie to the collection."""
        try:
            if not isinstance(movie, Movie):
                raise ValueError("Invalid movie object")
            self.movies.append(movie)
            return self.save_movies()
        except Exception as e:
            print(f"Error adding movie: {e}")
            return False

    def remove_movie(self, index):
        """Remove a movie by index."""
        try:
            if 0 <= index < len(self.movies):
                self.movies.pop(index)
                return self.save_movies()
            return False
        except Exception as e:
            print(f"Error removing movie: {e}")
            return False

    def update_movie(self, index, movie):
        """Update a movie at given index."""
        try:
            if 0 <= index < len(self.movies) and isinstance(movie, Movie):
                self.movies[index] = movie
                return self.save_movies()
            return False
        except Exception as e:
            print(f"Error updating movie: {e}")
            return False

    def search_movies(self, query):
        """Search movies by title, director, or cast."""
        try:
            query = query.lower().strip()
            if not query:
                return self.movies
            results = []
            for movie in self.movies:
                if (query in movie.title.lower() or
                    query in movie.director.lower() or
                    any(query in c.lower() for c in movie.cast) or
                    query in movie.genre.lower()):
                    results.append(movie)
            return results
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def get_sorted_by_imdb(self, reverse=True):
        """Get movies sorted by IMDb rating."""
        try:
            return sorted(self.movies,
                         key=lambda m: float(m.imdb_rating) if m.imdb_rating else 0,
                         reverse=reverse)
        except Exception as e:
            print(f"Error sorting: {e}")
            return self.movies

    def get_sorted_by_director(self):
        """Get movies sorted by director name."""
        try:
            return sorted(self.movies, key=lambda m: m.director.lower())
        except Exception as e:
            print(f"Error sorting: {e}")
            return self.movies

    def get_sorted_by_cast(self):
        """Get movies sorted by first cast member."""
        try:
            return sorted(self.movies,
                         key=lambda m: m.cast[0].lower() if m.cast else "")
        except Exception as e:
            print(f"Error sorting: {e}")
            return self.movies

    def get_all_directors(self):
        """Get unique list of directors."""
        return list(set(m.director for m in self.movies if m.director))

    def get_all_genres(self):
        """Get unique list of genres."""
        return list(set(m.genre for m in self.movies if m.genre))

    @property
    def count(self):
        return len(self.movies)
