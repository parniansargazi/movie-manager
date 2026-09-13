"""Build a top-100-movies dataset enriched from Wikipedia/Wikidata.

Fetches, for each film in the IMDb-style top list:
  - plot/description, poster, year, genre
  - director (bio + photo)
  - up to 3 main cast members (photos + short bios)

Outputs a merged movies.json for the Movie Manager app.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "MovieManagerBuilder/1.0 (personal movie library; contact: user@localhost)"}
DATA_FILE = "movies.json"
CACHE_FILE = "_wikicache.json"
import time


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CACHE = load_cache()

import threading
_rate_lock = threading.Lock()
_last_req = 0.0
MIN_GAP = 0.35  # seconds between requests (global rate gate)


def http_json(url):
    global _last_req
    for attempt in range(5):
        with _rate_lock:
            wait = MIN_GAP - (time.time() - _last_req)
            if wait > 0:
                time.sleep(wait)
            _last_req = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 4:
                time.sleep(2.0 * (attempt + 1))
                continue
            if attempt == 4:
                raise
            continue
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.0 * (attempt + 1))


# title, year, director, genre, imdb rating, cast, optional wikipedia page hint
FILMS = [
    {"title": "The Shawshank Redemption", "year": "1994", "director": "Frank Darabont", "genre": "Drama", "imdb": 9.3, "cast": ["Tim Robbins", "Morgan Freeman", "Bob Gunton"]},
    {"title": "The Godfather", "year": "1972", "director": "Francis Ford Coppola", "genre": "Crime", "imdb": 9.2, "cast": ["Marlon Brando", "Al Pacino", "James Caan"]},
    {"title": "The Dark Knight", "year": "2008", "director": "Christopher Nolan", "genre": "Action", "imdb": 9.0, "cast": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"]},
    {"title": "The Godfather Part II", "year": "1974", "director": "Francis Ford Coppola", "genre": "Crime", "imdb": 9.0, "cast": ["Al Pacino", "Robert De Niro", "Diane Keaton"]},
    {"title": "12 Angry Men", "year": "1957", "director": "Sidney Lumet", "genre": "Drama", "imdb": 9.0, "cast": ["Henry Fonda", "Lee J. Cobb", "Martin Balsam"], "page": "12 Angry Men (1957 film)"},
    {"title": "Schindler's List", "year": "1993", "director": "Steven Spielberg", "genre": "Drama", "imdb": 9.0, "cast": ["Liam Neeson", "Ralph Fiennes", "Ben Kingsley"]},
    {"title": "The Lord of the Rings: The Return of the King", "year": "2003", "director": "Peter Jackson", "genre": "Fantasy", "imdb": 9.0, "cast": ["Elijah Wood", "Viggo Mortensen", "Ian McKellen"]},
    {"title": "Pulp Fiction", "year": "1994", "director": "Quentin Tarantino", "genre": "Crime", "imdb": 8.9, "cast": ["John Travolta", "Uma Thurman", "Samuel L. Jackson"]},
    {"title": "The Lord of the Rings: The Fellowship of the Ring", "year": "2001", "director": "Peter Jackson", "genre": "Fantasy", "imdb": 8.8, "cast": ["Elijah Wood", "Ian McKellen", "Viggo Mortensen"]},
    {"title": "The Good, the Bad and the Ugly", "year": "1966", "director": "Sergio Leone", "genre": "Western", "imdb": 8.8, "cast": ["Clint Eastwood", "Eli Wallach", "Lee Van Cleef"]},
    {"title": "Forrest Gump", "year": "1994", "director": "Robert Zemeckis", "genre": "Drama", "imdb": 8.8, "cast": ["Tom Hanks", "Robin Wright", "Gary Sinise"]},
    {"title": "The Lord of the Rings: The Two Towers", "year": "2002", "director": "Peter Jackson", "genre": "Fantasy", "imdb": 8.8, "cast": ["Elijah Wood", "Ian McKellen", "Viggo Mortensen"]},
    {"title": "Fight Club", "year": "1999", "director": "David Fincher", "genre": "Drama", "imdb": 8.8, "cast": ["Brad Pitt", "Edward Norton", "Helena Bonham Carter"]},
    {"title": "Inception", "year": "2010", "director": "Christopher Nolan", "genre": "Sci-Fi", "imdb": 8.8, "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"]},
    {"title": "Star Wars: Episode V - The Empire Strikes Back", "year": "1980", "director": "Irvin Kershner", "genre": "Sci-Fi", "imdb": 8.7, "cast": ["Mark Hamill", "Harrison Ford", "Carrie Fisher"]},
    {"title": "The Matrix", "year": "1999", "director": "Lana Wachowski", "genre": "Sci-Fi", "imdb": 8.7, "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"]},
    {"title": "Goodfellas", "year": "1990", "director": "Martin Scorsese", "genre": "Crime", "imdb": 8.7, "cast": ["Ray Liotta", "Joe Pesci", "Robert De Niro"]},
    {"title": "One Flew Over the Cuckoo's Nest", "year": "1975", "director": "Milos Forman", "genre": "Drama", "imdb": 8.7, "cast": ["Jack Nicholson", "Louise Fletcher", "Will Sampson"]},
    {"title": "Seven Samurai", "year": "1954", "director": "Akira Kurosawa", "genre": "Drama", "imdb": 8.6, "cast": ["Toshiro Mifune", "Takashi Shimura", "Keiko Tsushima"], "page": "Seven Samurai"},
    {"title": "Se7en", "year": "1995", "director": "David Fincher", "genre": "Crime", "imdb": 8.6, "cast": ["Brad Pitt", "Morgan Freeman", "Kevin Spacey"], "page": "Seven (1995 film)"},
    {"title": "The Silence of the Lambs", "year": "1991", "director": "Jonathan Demme", "genre": "Crime", "imdb": 8.6, "cast": ["Anthony Hopkins", "Jodie Foster", "Scott Glenn"]},
    {"title": "It's a Wonderful Life", "year": "1946", "director": "Frank Capra", "genre": "Drama", "imdb": 8.6, "cast": ["James Stewart", "Donna Reed", "Lionel Barrymore"]},
    {"title": "Life Is Beautiful", "year": "1997", "director": "Roberto Benigni", "genre": "Comedy", "imdb": 8.6, "cast": ["Roberto Benigni", "Nicoletta Braschi", "Giorgio Cantarini"]},
    {"title": "Saving Private Ryan", "year": "1998", "director": "Steven Spielberg", "genre": "War", "imdb": 8.6, "cast": ["Tom Hanks", "Matt Damon", "Tom Sizemore"]},
    {"title": "Spirited Away", "year": "2001", "director": "Hayao Miyazaki", "genre": "Animation", "imdb": 8.6, "cast": ["Rumi Hiiragi", "Miyu Irino", "Mari Natsuki"]},
    {"title": "Interstellar", "year": "2014", "director": "Christopher Nolan", "genre": "Sci-Fi", "imdb": 8.7, "cast": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"]},
    {"title": "The Green Mile", "year": "1999", "director": "Frank Darabont", "genre": "Drama", "imdb": 8.6, "cast": ["Tom Hanks", "Michael Clarke Duncan", "David Morse"]},
    {"title": "Léon: The Professional", "year": "1994", "director": "Luc Besson", "genre": "Crime", "imdb": 8.5, "cast": ["Jean Reno", "Natalie Portman", "Gary Oldman"], "page": "Léon: The Professional"},
    {"title": "City of God", "year": "2002", "director": "Fernando Meirelles", "genre": "Crime", "imdb": 8.6, "cast": ["Alexandre Rodrigues", "Leandro Firmino", "Phellipe Haagensen"]},
    {"title": "The Pianist", "year": "2002", "director": "Roman Polanski", "genre": "Drama", "imdb": 8.5, "cast": ["Adrien Brody", "Thomas Kretschmann", "Emilia Fox"]},
    {"title": "The Departed", "year": "2006", "director": "Martin Scorsese", "genre": "Crime", "imdb": 8.5, "cast": ["Leonardo DiCaprio", "Matt Damon", "Jack Nicholson"]},
    {"title": "The Usual Suspects", "year": "1995", "director": "Bryan Singer", "genre": "Crime", "imdb": 8.5, "cast": ["Kevin Spacey", "Gabriel Byrne", "Chazz Palminteri"]},
    {"title": "Terminator 2: Judgment Day", "year": "1991", "director": "James Cameron", "genre": "Sci-Fi", "imdb": 8.6, "cast": ["Arnold Schwarzenegger", "Linda Hamilton", "Edward Furlong"]},
    {"title": "Cinema Paradiso", "year": "1988", "director": "Giuseppe Tornatore", "genre": "Drama", "imdb": 8.5, "cast": ["Philippe Noiret", "Enzo Cannavale", "Antonella Attili"]},
    {"title": "American History X", "year": "1998", "director": "Tony Kaye", "genre": "Drama", "imdb": 8.5, "cast": ["Edward Norton", "Edward Furlong", "Beverly D'Angelo"]},
    {"title": "Gladiator", "year": "2000", "director": "Ridley Scott", "genre": "Action", "imdb": 8.5, "cast": ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen"]},
    {"title": "The Prestige", "year": "2006", "director": "Christopher Nolan", "genre": "Mystery", "imdb": 8.5, "cast": ["Christian Bale", "Hugh Jackman", "Scarlett Johansson"]},
    {"title": "The Lion King", "year": "1994", "director": "Roger Allers", "genre": "Animation", "imdb": 8.5, "cast": ["Matthew Broderick", "Jeremy Irons", "James Earl Jones"]},
    {"title": "Back to the Future", "year": "1985", "director": "Robert Zemeckis", "genre": "Sci-Fi", "imdb": 8.5, "cast": ["Michael J. Fox", "Christopher Lloyd", "Lea Thompson"]},
    {"title": "Whiplash", "year": "2014", "director": "Damien Chazelle", "genre": "Drama", "imdb": 8.5, "cast": ["Miles Teller", "J.K. Simmons", "Paul Reiser"]},
    {"title": "Parasite", "year": "2019", "director": "Bong Joon-ho", "genre": "Thriller", "imdb": 8.5, "cast": ["Song Kang-ho", "Cho Yeo-jeong", "Choi Woo-shik"]},
    {"title": "The Intouchables", "year": "2011", "director": "Olivier Nakache", "genre": "Comedy", "imdb": 8.5, "cast": ["François Cluzet", "Omar Sy", "Anne Le Ny"]},
    {"title": "Alien", "year": "1979", "director": "Ridley Scott", "genre": "Horror", "imdb": 8.5, "cast": ["Sigourney Weaver", "Tom Skerritt", "John Hurt"]},
    {"title": "Django Unchained", "year": "2012", "director": "Quentin Tarantino", "genre": "Western", "imdb": 8.4, "cast": ["Jamie Foxx", "Christoph Waltz", "Leonardo DiCaprio"]},
    {"title": "Grave of the Fireflies", "year": "1988", "director": "Isao Takahata", "genre": "Animation", "imdb": 8.5, "cast": ["Tsutomu Tatsumi", "Ayano Shiraishi", "Yoshiko Shinohara"]},
    {"title": "The Dark Knight Rises", "year": "2012", "director": "Christopher Nolan", "genre": "Action", "imdb": 8.4, "cast": ["Christian Bale", "Tom Hardy", "Anne Hathaway"]},
    {"title": "Once Upon a Time in the West", "year": "1968", "director": "Sergio Leone", "genre": "Western", "imdb": 8.5, "cast": ["Henry Fonda", "Claudia Cardinale", "Charles Bronson"]},
    {"title": "WALL-E", "year": "2008", "director": "Andrew Stanton", "genre": "Animation", "imdb": 8.4, "cast": ["Ben Burtt", "Elissa Knight", "Jeff Garlin"]},
    {"title": "Memento", "year": "2000", "director": "Christopher Nolan", "genre": "Mystery", "imdb": 8.4, "cast": ["Guy Pearce", "Carrie-Anne Moss", "Joe Pantoliano"]},
    {"title": "Apocalypse Now", "year": "1979", "director": "Francis Ford Coppola", "genre": "War", "imdb": 8.4, "cast": ["Martin Sheen", "Marlon Brando", "Robert Duvall"]},
    {"title": "The Great Dictator", "year": "1940", "director": "Charlie Chaplin", "genre": "Comedy", "imdb": 8.4, "cast": ["Charlie Chaplin", "Paulette Goddard", "Jack Oakie"]},
    {"title": "The Shining", "year": "1980", "director": "Stanley Kubrick", "genre": "Horror", "imdb": 8.4, "cast": ["Jack Nicholson", "Shelley Duvall", "Danny Lloyd"]},
    {"title": "Paths of Glory", "year": "1957", "director": "Stanley Kubrick", "genre": "War", "imdb": 8.4, "cast": ["Kirk Douglas", "Ralph Meeker", "Adolphe Menjou"]},
    {"title": "Oldboy", "year": "2003", "director": "Park Chan-wook", "genre": "Thriller", "imdb": 8.4, "cast": ["Choi Min-sik", "Yoo Ji-tae", "Kang Hye-jung"], "page": "Oldboy (2003 film)"},
    {"title": "The Lives of Others", "year": "2006", "director": "Florian Henckel von Donnersmarck", "genre": "Thriller", "imdb": 8.4, "cast": ["Ulrich Mühe", "Martina Gedeck", "Sebastian Koch"]},
    {"title": "Sunset Boulevard", "year": "1950", "director": "Billy Wilder", "genre": "Drama", "imdb": 8.4, "cast": ["William Holden", "Gloria Swanson", "Erich von Stroheim"], "page": "Sunset Boulevard (film)"},
    {"title": "Princess Mononoke", "year": "1997", "director": "Hayao Miyazaki", "genre": "Animation", "imdb": 8.3, "cast": ["Yōji Matsuda", "Yuriko Ishida", "Yūko Tanaka"]},
    {"title": "Modern Times", "year": "1936", "director": "Charlie Chaplin", "genre": "Comedy", "imdb": 8.5, "cast": ["Charlie Chaplin", "Paulette Goddard", "Henry Bergman"]},
    {"title": "Vertigo", "year": "1958", "director": "Alfred Hitchcock", "genre": "Mystery", "imdb": 8.3, "cast": ["James Stewart", "Kim Novak", "Barbara Bel Geddes"]},
    {"title": "Requiem for a Dream", "year": "2000", "director": "Darren Aronofsky", "genre": "Drama", "imdb": 8.3, "cast": ["Ellen Burstyn", "Jared Leto", "Jennifer Connelly"]},
    {"title": "Eternal Sunshine of the Spotless Mind", "year": "2004", "director": "Michel Gondry", "genre": "Romance", "imdb": 8.3, "cast": ["Jim Carrey", "Kate Winslet", "Kirsten Dunst"]},
    {"title": "Amélie", "year": "2001", "director": "Jean-Pierre Jeunet", "genre": "Romance", "imdb": 8.3, "cast": ["Audrey Tautou", "Mathieu Kassovitz", "Rufus"], "page": "Amélie"},
    {"title": "The Lion King", "year": "1994", "director": "Roger Allers", "genre": "Animation", "imdb": 8.5, "cast": ["Matthew Broderick", "Jeremy Irons", "James Earl Jones"]},
    {"title": "North by Northwest", "year": "1959", "director": "Alfred Hitchcock", "genre": "Thriller", "imdb": 8.3, "cast": ["Cary Grant", "Eva Marie Saint", "James Mason"]},
    {"title": "Aliens", "year": "1986", "director": "James Cameron", "genre": "Sci-Fi", "imdb": 8.4, "cast": ["Sigourney Weaver", "Michael Biehn", "Carrie Henn"], "page": "Aliens (film)"},
    {"title": "Reservoir Dogs", "year": "1992", "director": "Quentin Tarantino", "genre": "Crime", "imdb": 8.3, "cast": ["Harvey Keitel", "Tim Roth", "Michael Madsen"]},
    {"title": "Good Will Hunting", "year": "1997", "director": "Gus Van Sant", "genre": "Drama", "imdb": 8.3, "cast": ["Matt Damon", "Robin Williams", "Ben Affleck"]},
    {"title": "American Beauty", "year": "1999", "director": "Sam Mendes", "genre": "Drama", "imdb": 8.3, "cast": ["Kevin Spacey", "Annette Bening", "Thora Birch"]},
    {"title": "Toy Story", "year": "1995", "director": "John Lasseter", "genre": "Animation", "imdb": 8.3, "cast": ["Tom Hanks", "Tim Allen", "Don Rickles"]},
    {"title": "2001: A Space Odyssey", "year": "1968", "director": "Stanley Kubrick", "genre": "Sci-Fi", "imdb": 8.3, "cast": ["Keir Dullea", "Gary Lockwood", "William Sylvester"]},
    {"title": "Braveheart", "year": "1995", "director": "Mel Gibson", "genre": "Drama", "imdb": 8.3, "cast": ["Mel Gibson", "Sophie Marceau", "Patrick McGoohan"]},
    {"title": "Singin' in the Rain", "year": "1952", "director": "Stanley Donen", "genre": "Musical", "imdb": 8.3, "cast": ["Gene Kelly", "Donald O'Connor", "Debbie Reynolds"], "page": "Singin' in the Rain"},
    {"title": "The Third Man", "year": "1949", "director": "Carol Reed", "genre": "Thriller", "imdb": 8.2, "cast": ["Orson Welles", "Joseph Cotten", "Alida Valli"]},
    {"title": "Double Indemnity", "year": "1944", "director": "Billy Wilder", "genre": "Crime", "imdb": 8.3, "cast": ["Fred MacMurray", "Barbara Stanwyck", "Edward G. Robinson"]},
    {"title": "The Great Dictator", "year": "1940", "director": "Charlie Chaplin", "genre": "Comedy", "imdb": 8.4, "cast": ["Charlie Chaplin", "Paulette Goddard", "Jack Oakie"]},
    {"title": "Heat", "year": "1995", "director": "Michael Mann", "genre": "Crime", "imdb": 8.3, "cast": ["Al Pacino", "Robert De Niro", "Val Kilmer"]},
    {"title": "The Apartment", "year": "1960", "director": "Billy Wilder", "genre": "Comedy", "imdb": 8.3, "cast": ["Jack Lemmon", "Shirley MacLaine", "Fred MacMurray"]},
    {"title": "Requiem for a Dream", "year": "2000", "director": "Darren Aronofsky", "genre": "Drama", "imdb": 8.3, "cast": ["Ellen Burstyn", "Jared Leto", "Jennifer Connelly"]},
    {"title": "Joker", "year": "2019", "director": "Todd Phillips", "genre": "Crime", "imdb": 8.4, "cast": ["Joaquin Phoenix", "Robert De Niro", "Zazie Beetz"]},
    {"title": "Full Metal Jacket", "year": "1987", "director": "Stanley Kubrick", "genre": "War", "imdb": 8.3, "cast": ["Matthew Modine", "R. Lee Ermey", "Vincent D'Onofrio"]},
    {"title": "Scarface", "year": "1983", "director": "Brian De Palma", "genre": "Crime", "imdb": 8.3, "cast": ["Al Pacino", "Michelle Pfeiffer", "Steven Bauer"], "page": "Scarface (1983 film)"},
    {"title": "Rashomon", "year": "1950", "director": "Akira Kurosawa", "genre": "Mystery", "imdb": 8.2, "cast": ["Toshiro Mifune", "Machiko Kyō", "Masayuki Mori"]},
    {"title": "Citizen Kane", "year": "1941", "director": "Orson Welles", "genre": "Drama", "imdb": 8.3, "cast": ["Orson Welles", "Joseph Cotten", "Dorothy Comingore"]},
    {"title": "Lawrence of Arabia", "year": "1962", "director": "David Lean", "genre": "Adventure", "imdb": 8.3, "cast": ["Peter O'Toole", "Alec Guinness", "Omar Sharif"]},
    {"title": "The Hunt", "year": "2012", "director": "Thomas Vinterberg", "genre": "Drama", "imdb": 8.3, "cast": ["Mads Mikkelsen", "Thomas Bo Larsen", "Annika Wedderkopp"], "page": "The Hunt (2012 film)"},
    {"title": "Raging Bull", "year": "1980", "director": "Martin Scorsese", "genre": "Sport", "imdb": 8.2, "cast": ["Robert De Niro", "Cathy Moriarty", "Joe Pesci"]},
    {"title": "No Country for Old Men", "year": "2007", "director": "Joel Coen", "genre": "Thriller", "imdb": 8.2, "cast": ["Javier Bardem", "Josh Brolin", "Tommy Lee Jones"]},
    {"title": "Amadeus", "year": "1984", "director": "Milos Forman", "genre": "Drama", "imdb": 8.4, "cast": ["F. Murray Abraham", "Tom Hulce", "Elizabeth Berridge"]},
    {"title": "A Clockwork Orange", "year": "1971", "director": "Stanley Kubrick", "genre": "Crime", "imdb": 8.3, "cast": ["Malcolm McDowell", "Patrick Magee", "Michael Bates"]},
    {"title": "The Truman Show", "year": "1998", "director": "Peter Weir", "genre": "Comedy", "imdb": 8.2, "cast": ["Jim Carrey", "Laura Linney", "Ed Harris"]},
    {"title": "Up", "year": "2009", "director": "Pete Docter", "genre": "Animation", "imdb": 8.3, "cast": ["Ed Asner", "Jordan Nagai", "Christopher Plummer"]},
    {"title": "Toy Story 3", "year": "2010", "director": "Lee Unkrich", "genre": "Animation", "imdb": 8.2, "cast": ["Tom Hanks", "Tim Allen", "Joan Cusack"]},
    {"title": "Taxi Driver", "year": "1976", "director": "Martin Scorsese", "genre": "Crime", "imdb": 8.2, "cast": ["Robert De Niro", "Jodie Foster", "Cybill Shepherd"]},
    {"title": "Inglourious Basterds", "year": "2009", "director": "Quentin Tarantino", "genre": "War", "imdb": 8.4, "cast": ["Brad Pitt", "Christoph Waltz", "Mélanie Laurent"]},
    {"title": "Snatch", "year": "2000", "director": "Guy Ritchie", "genre": "Crime", "imdb": 8.2, "cast": ["Jason Statham", "Brad Pitt", "Stephen Graham"]},
    {"title": "The Wolf of Wall Street", "year": "2013", "director": "Martin Scorsese", "genre": "Biography", "imdb": 8.2, "cast": ["Leonardo DiCaprio", "Jonah Hill", "Margot Robbie"]},
    {"title": "Die Hard", "year": "1988", "director": "John McTiernan", "genre": "Action", "imdb": 8.2, "cast": ["Bruce Willis", "Alan Rickman", "Bonnie Bedelia"], "page": "Die Hard"},
    {"title": "Metropolis", "year": "1927", "director": "Fritz Lang", "genre": "Sci-Fi", "imdb": 8.3, "cast": ["Brigitte Helm", "Alfred Abel", "Gustav Fröhlich"]},
    {"title": "The Seventh Seal", "year": "1957", "director": "Ingmar Bergman", "genre": "Drama", "imdb": 8.1, "cast": ["Max von Sydow", "Bengt Ekerot", "Nils Poppe"]},
    {"title": "Unforgiven", "year": "1992", "director": "Clint Eastwood", "genre": "Western", "imdb": 8.2, "cast": ["Clint Eastwood", "Gene Hackman", "Morgan Freeman"]},
    {"title": "Ikiru", "year": "1952", "director": "Akira Kurosawa", "genre": "Drama", "imdb": 8.3, "cast": ["Takashi Shimura", "Nobuo Kaneko", "Shin'ichi Himori"], "page": "Ikiru"},
    {"title": "Harakiri", "year": "1962", "director": "Masaki Kobayashi", "genre": "Drama", "imdb": 8.6, "cast": ["Tatsuya Nakadai", "Akira Ishihama", "Shima Iwashita"], "page": "Harakiri (1962 film)"},
    {"title": "The Sting", "year": "1973", "director": "George Roy Hill", "genre": "Crime", "imdb": 8.3, "cast": ["Paul Newman", "Robert Redford", "Robert Shaw"]},
    {"title": "Monty Python and the Holy Grail", "year": "1975", "director": "Terry Gilliam", "genre": "Comedy", "imdb": 8.2, "cast": ["Graham Chapman", "John Cleese", "Eric Idle"]},
    {"title": "The Grand Budapest Hotel", "year": "2014", "director": "Wes Anderson", "genre": "Comedy", "imdb": 8.1, "cast": ["Ralph Fiennes", "F. Murray Abraham", "Tony Revolori"]},
]


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_summary(title, suffixes=None):
    """Fetch Wikipedia REST summary for a page title; returns dict or None.

    Only accepts a 'standard' article page (skips disambiguation/redirects),
    trying extra title suffixes until it finds one.
    """
    suffixes = suffixes or ["", " (film)", " (movie)", " (actor)"]
    for sfx in suffixes:
        candidate = title + sfx
        key = candidate.replace(" ", "_")
        if key in CACHE:
            data = CACHE[key]
            if data and data.get("type") == "standard" and data.get("extract"):
                return data
            continue
        try:
            enc = urllib.parse.quote(key)
            data = http_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + enc)
            CACHE[key] = data
            if data.get("type") == "standard" and data.get("extract"):
                return data
        except Exception:
            continue
    return None


def truncate(text, limit):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit].rsplit(" ", 1)[0] + "..."


WIKI_LINK = re.compile(r"\[(?:[^|\]]*\|)?([^\]]*)\]")


def summary_extract(data, limit):
    if not data:
        return ""
    text = data.get("extract", "")
    text = WIKI_LINK.sub(r"\1", text)
    return truncate(text, limit)


def summary_image(data):
    if not data:
        return ""
    thumb = data.get("thumbnail") or {}
    return thumb.get("source", "")


def enrich_film(entry):
    """Fetch all enrichment for one film. Returns a movie dict."""
    title = entry["title"]
    hint = entry.get("page")

    film_data = fetch_summary(hint or title)

    name_cache = {}

    def person(name):
        if name in name_cache:
            return name_cache[name]
        data = fetch_summary(name)
        name_cache[name] = data
        return data

    director_data = person(entry["director"])
    cast_images = []
    cast_bios = []
    for actor in entry["cast"][:3]:
        adata = person(actor)
        if adata:
            cast_images.append(summary_image(adata))
            bio = summary_extract(adata, 160)
            if bio:
                cast_bios.append(f"{actor}: {bio}")

    movie = {
        "title": title,
        "director": entry["director"],
        "cast": list(entry["cast"][:3]),
        "description": summary_extract(film_data, 600),
        "imdb_rating": entry["imdb"],
        "director_bio": summary_extract(director_data, 350),
        "cast_bio": "\n".join(cast_bios),
        "director_image": summary_image(director_data),
        "cast_images": cast_images,
        "poster": summary_image(film_data),
        "year": entry["year"],
        "genre": entry["genre"],
        "date_added": "From Top 100",
    }
    return movie


def repair(results):
    """Retry filling in missing fields, slowly, until covered."""
    for title, movie in results.items():
        if not movie["description"]:
            hint = next((e.get("page") for e in FILMS if e["title"] == title), None)
            for attempt in range(6):
                data = fetch_summary(hint or title)
                if data:
                    movie["description"] = summary_extract(data, 600)
                    movie["poster"] = summary_image(data)
                    break
                time.sleep(1.5 * (attempt + 1))
        if not movie["director_bio"]:
            for attempt in range(6):
                data = fetch_summary(movie["director"])
                if data:
                    movie["director_bio"] = summary_extract(data, 350)
                    movie["director_image"] = summary_image(data)
                    break
                time.sleep(1.5 * (attempt + 1))
        if not movie["cast_images"]:
            bios = []
            imgs = []
            for actor in movie["cast"]:
                data = None
                for attempt in range(3):
                    data = fetch_summary(actor)
                    if data:
                        break
                    time.sleep(1.5 * (attempt + 1))
                if data:
                    imgs.append(summary_image(data))
                    bio = summary_extract(data, 160)
                    if bio:
                        bios.append(f"{actor}: {bio}")
            movie["cast_images"] = imgs
            movie["cast_bio"] = "\n".join(bios)


def main():
    print(f"Enriching {len(FILMS)} films...")

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(enrich_film, e): e["title"] for e in FILMS}
        for i, fut in enumerate(as_completed(futures), 1):
            title = futures[fut]
            try:
                results[title] = fut.result()
                print(f"[{i}/{len(FILMS)}] {title}")
            except Exception as ex:
                print(f"[{i}/{len(FILMS)}] {title} FAILED: {ex}")

    print("Repairing missing fields...")
    repair(results)

    existing = []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

    keep = [m for m in existing if m.get("title") not in results]
    merged = list(results.values()) + keep
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    ok = sum(1 for m in results.values() if m["poster"])
    bio = sum(1 for m in results.values() if m["director_bio"])
    print(f"\nDone. {len(results)} films in movies.json | posters: {ok} | director bios: {bio}")

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False)


if __name__ == "__main__":
    main()