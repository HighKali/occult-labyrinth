import pygame
import socket
import threading
import sqlite3
import random
import json
import hashlib
import sys
import time

# Inizializzazione Pygame
try:
    pygame.init()
    WINDOW_SIZE = (800, 600)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Occult Labyrinth: Shadows of Baphomet")
    clock = pygame.time.Clock()
except Exception as e:
    print(f"Errore inizializzazione Pygame: {e}")
    sys.exit(1)

# Colori
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GRAY = (50, 50, 50)

# Sistema di Token (Essenza Oscura)
def generate_token(username, counter):
    token_data = f"{username}{counter}{random.randint(1, 1000)}".encode()
    token_hash = hashlib.sha256(token_data).hexdigest()[:8]
    return {"id": token_hash, "value": random.randint(5, 15)}  # Valore variabile per imprevedibilità

# Database
try:
    conn = sqlite3.connect("occult_labyrinth.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        username TEXT PRIMARY KEY, hp INTEGER, strength INTEGER,
        intelligence INTEGER, luck INTEGER, inventory TEXT, room INTEGER, essence INTEGER, token_counter INTEGER)""")
    c.execute("CREATE TABLE IF NOT EXISTS progress (username TEXT, mission TEXT, completed INTEGER)")
    conn.commit()
except sqlite3.Error as e:
    print(f"Errore database: {e}")
    sys.exit(1)

# Suoni inquietanti
try:
    pygame.mixer.init()
    def play_sound(frequency, duration):
        sample = pygame.mixer.Sound(pygame.sndarray.make_sound(
            pygame.sndarray.samples([int(32767 * (i % frequency) / frequency) - random.randint(0, 1000) for i in range(int(44100 * duration))])))
        sample.play()
except Exception:
    def play_sound(frequency, duration):
        print("(Suono non disponibile)")

# Telnet Server
class TelnetServer:
    def __init__(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(('localhost', 2323))
            self.server.listen(5)
            self.clients = {}
            self.lock = threading.Lock()
        except Exception as e:
            print(f"Errore server Telnet: {e}")
            sys.exit(1)

    def broadcast(self, message, sender):
        with self.lock:
            for client in list(self.clients):
                if client != sender:
                    try:
                        client.send(f"{message}\n".encode())
                    except:
                        pass

    def handle_client(self, client):
        try:
            client.send("Nome (il tuo destino è già scritto): ".encode())
            username = client.recv(1024).decode().strip()
            if not username:
                client.close()
                return
            with self.lock:
                self.clients[client] = username
            c.execute("INSERT OR IGNORE INTO players VALUES (?, 50, 8, 3, 2, ?, 1, 0, 0)",
                      (username, json.dumps({"frantumi d’osso": 1})))
            conn.commit()
            client.send(f"{username}, il buio ti reclama. HP iniziali ridotti per la tua fragilità mortale.\n".encode())
        except Exception as e:
            print(f"Errore connessione client: {e}")
            client.close()
            return

        while True:
            try:
                msg = client.recv(1024).decode().strip()
                if not msg:
                    break
                if msg.startswith("/move"): self.move_player(username, client)
                elif msg.startswith("/chat"): self.broadcast(f"{username} sussurra dal vuoto: {msg[6:]}", client)
                elif msg == "/dee": client.send("John Dee: 'Le ombre si nutrono della tua anima. La chiave è oltre il sangue.'\n".encode())
                else: client.send("Urla nel buio: /move, /chat, /dee\n".encode())
            except:
                break
        with self.lock:
            if client in self.clients:
                del self.clients[client]
        client.close()

    def move_player(self, username, client):
        try:
            c.execute("UPDATE players SET room = room + 1 WHERE username = ?", (username,))
            conn.commit()
            c.execute("SELECT room FROM players WHERE username = ?", (username,))
            room = c.fetchone()[0]
            client.send(f"Stanza {room}: il pavimento geme sotto il tuo peso.\n".encode())
        except sqlite3.Error as e:
            client.send(f"Errore nel vuoto: {e}\n".encode())

    def run(self):
        threading.Thread(target=self._run_server, daemon=True).start()

    def _run_server(self):
        while True:
            try:
                client, _ = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except Exception as e:
                print(f"Errore accettazione client: {e}")

# Gioco
class Game:
    def __init__(self):
        self.server = TelnetServer()
        self.server.run()
        self.player = {"pos": [50, 50], "size": 20}
        self.walls = [
            pygame.Rect(0, 0, 800, 20), pygame.Rect(0, 580, 800, 20),
            pygame.Rect(200, 100, 20, 400), pygame.Rect(600, 200, 20, 300)
        ]
        self.monsters = [
            {"name": "Ombra Strisciante", "hp": 60, "damage": 20, "pos": [300, 300], "size": 30, "color": GRAY},
            {"name": "Spettro Urlante", "hp": 80, "damage": 25, "pos": [400, 400], "size": 40, "color": BLUE}
        ]
        self.missions = {
            "Il Segno della Fine": False,
            "Sussurri nell’Oblio": False,
            "Il Patto Spezzato": False,
            "L’Occhio di Dee": False,
            "Abbraccio di Baphomet": False
        }
        self.current_room = 1
        self.glitch_timer = 0

    def load_player(self, username):
        try:
            c.execute("SELECT * FROM players WHERE username = ?", (username,))
            data = c.fetchone()
            if data:
                self.player.update({
                    "hp": data[1], "strength": data[2], "intelligence": data[3], "luck": data[4],
                    "inventory": json.loads(data[5]), "room": data[6], "essence": data[7], "token_counter": data[8]
                })
                self.current_room = data[6]
            else:
                print("Nessuna traccia di te nel buio. Connettiti via Telnet.")
                sys.exit(1)
            self.username = username
        except sqlite3.Error as e:
            print(f"Errore nel richiamare la tua anima: {e}")
            sys.exit(1)

    def save_progress(self):
        try:
            c.execute("UPDATE players SET hp=?, room=?, essence=?, token_counter=? WHERE username=?",
                      (self.player["hp"], self.current_room, self.player.get("essence", 0), self.player.get("token_counter", 0), self.username))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Errore nel sigillare il tuo destino: {e}")

    def mine_token(self):
        token_counter = self.player.get("token_counter", 0)
        new_token = generate_token(self.username, token_counter)
        self.player["essence"] = self.player.get("essence", 0) + new_token["value"]
        self.player["token_counter"] = token_counter + 1
        print(f"L’Essenza Oscura si condensa: {self.player['essence']} (Sigillo: {new_token['id']})")

    def combat(self, monster):
        play_sound(150, 0.3)  # Suono grave e distorto
        damage = random.randint(1, self.player["strength"]) - random.randint(0, 3)  # Imprevedibilità
        if damage < 0: damage = 0
        monster["hp"] -= damage
        print(f"Hai colpito {monster['name']} con {damage} forza, ma il buio ti guarda.")
        if monster["hp"] <= 0:
            self.monsters.remove(monster)
            self.mine_token()
            print(f"{monster['name']} si dissolve in un lamento. Qualcosa ti osserva ancora.")
        else:
            self.player["hp"] -= monster["damage"] + random.randint(0, 5)  # Danno variabile
            print(f"{monster['name']} ti squarcia per {monster['damage']} HP. Il sangue chiama.")
            play_sound(300, 0.5)
            if self.player["hp"] <= 0:
                print("Le ombre ti hanno reclamato. Il tuo corpo resta nel labirinto.")
                return False
        return True

    def run(self):
        username = input("Chi osa entrare (nome)? ")
        self.load_player(username)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Movimento
            keys = pygame.key.get_pressed()
            new_pos = self.player["pos"].copy()
            if keys[pygame.K_LEFT]: new_pos[0] -= 5
            if keys[pygame.K_RIGHT]: new_pos[0] += 5
            if keys[pygame.K_UP]: new_pos[1] -= 5
            if keys[pygame.K_DOWN]: new_pos[1] += 5
            player_rect = pygame.Rect(new_pos[0], new_pos[1], self.player["size"], self.player["size"])
            if not any(player_rect.colliderect(wall) for wall in self.walls):
                self.player["pos"] = new_pos
                play_sound(400, 0.1)  # Passi distorti
                if random.random() < 0.1:  # 10% di probabilità di evento casuale
                    print("Un sussurro ti sfiora: 'Non c’è uscita.'")

            # Combattimento
            for monster in self.monsters[:]:
                if player_rect.colliderect(pygame.Rect(monster["pos"][0], monster["pos"][1], monster["size"], monster["size"])):
                    if not self.combat(monster):
                        running = False

            # Missioni inquietanti
            if self.current_room == 1 and not self.missions["Il Segno della Fine"]:
                print("Un cranio ti fissa. Rispondi: 'Chi dorme nel silenzio eterno?'")
                if input("> ").lower() == "i morti":
                    self.missions["Il Segno della Fine"] = True
                    self.mine_token()
                    print("Il cranio ride. Una porta si apre nel nulla.")
                    self.current_room += 1
                else:
                    self.player["hp"] -= 10
                    print("Un vento gelido ti colpisce. -10 HP.")
            elif self.current_room == 2 and not self.missions["Sussurri nell’Oblio"]:
                print("Voci dal muro: 'Sacrifica (hp) o fuggi (nessun progresso)?'")
                choice = input("> ").lower()
                if choice == "hp":
                    self.player["hp"] -= 15
                    self.missions["Sussurri nell’Oblio"] = True
                    self.mine_token()
                    print("Il tuo sangue tinge il pavimento. Avanzi.")
                    self.current_room += 1
                elif choice == "fuggi":
                    print("Le voci ridono. Resti fermo.")
            elif self.current_room == 5 and not self.missions["L’Occhio di Dee"]:
                print("Un’ombra ti parla via Telnet (/dee). Obbedisci o perdi tutto.")
                self.missions["L’Occhio di Dee"] = True
                self.mine_token()
                self.current_room += 1
            elif self.current_room == 7 and not self.missions["Abbraccio di Baphomet"]:
                print("Baphomet emerge: 'Unisciti a me (fine) o sfidami (morte)?'")
                choice = input("> ").lower()
                if choice == "unisciti":
                    self.missions["Abbraccio di Baphomet"] = True
                    print("Ti inchini. Il buio è casa tua. Fine.")
                    running = False
                elif choice == "sfidami":
                    self.monsters.append({"name": "Baphomet", "hp": 150, "damage": 40, "pos": [600, 300], "size": 50, "color": RED})

            # Glitch visivo
            self.glitch_timer += 1
            if self.glitch_timer % 30 == 0 and random.random() < 0.3:
                screen.fill(RED)
                pygame.display.flip()
                time.sleep(0.1)

            # Disegno
            screen.fill(BLACK)
            for wall in self.walls:
                pygame.draw.rect(screen, GRAY, wall)
            pygame.draw.rect(screen, RED, (self.player["pos"][0], self.player["pos"][1], self.player["size"], self.player["size"]))
            for monster in self.monsters:
                pygame.draw.rect(screen, monster["color"], (monster["pos"][0], monster["pos"][1], monster["size"], monster["size"]))
            pygame.display.flip()
            clock.tick(60)

            # Musica disturbante
            try:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(pygame.sndarray.make_sound(
                        pygame.sndarray.samples([int(32767 * (i % 80) / 80) - random.randint(0, 500) for i in range(44100 * 2)])))
                    pygame.mixer.music.play(-1)
            except:
                pass

        self.save_progress()
        pygame.quit()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except KeyboardInterrupt:
        print("Sei fuggito. Ma non davvero.")
    except Exception as e:
        print(f"Errore nel buio: {e}")
    finally:
        conn.close()
        pygame.quit()
