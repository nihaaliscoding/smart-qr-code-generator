import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import qrcode, sqlite3, hashlib
from PIL import Image, ImageTk

DB = "qr_app.db"
TYPES = ["Website / URL", "Text", "Email", "Phone", "Wi-Fi"]

def db(): return sqlite3.connect(DB)

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    try:
        c = db()
        c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, username TEXT UNIQUE, email TEXT, password TEXT);
            CREATE TABLE IF NOT EXISTS qr_codes(id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, qr_type TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
        c.commit(); c.close()
    except Exception as e: messagebox.showerror("Database Error", str(e))

class QRApp:
    def __init__(self, root):
        self.root, self.img = root, None
        self.root.title("Smart QR Code Generator")
        self.uid = self.uname = None
        self.login_screen()

    def screen(self, title):
        for w in self.root.winfo_children(): w.destroy()
        f = tk.Frame(self.root, padx=20, pady=10); f.pack()
        tk.Label(f, text=title, font=("Arial", 15, "bold")).pack(pady=8)
        return f
    def inp(self, p, label, show=""):
        tk.Label(p, text=label).pack()
        e = tk.Entry(p, show=show); e.pack()
        return e
    def login_screen(self):
        f = self.screen("Login")
        self.lu, self.lp = self.inp(f, "Username"), self.inp(f, "Password", "*")
        tk.Button(f, text="Login", command=self.login).pack(pady=6)
        tk.Button(f, text="Create Account", command=self.register_screen).pack()

    def login(self):
        try:
            u, p = self.lu.get().strip(), self.lp.get()
            if not u or not p: messagebox.showwarning("Login", "All fields are required."); return
            c = db(); r = c.execute("SELECT id,name,password FROM users WHERE username=?", (u,)).fetchone(); c.close()
            if not r or r[2] != hash_pw(p): messagebox.showerror("Login", "Invalid username or password."); return
            self.uid, self.uname = r[0], r[1]
            self.dashboard()
        except Exception as e: messagebox.showerror("Error", f"Login failed:\n{e}")

    def register_screen(self):
        f = self.screen("Register")
        self.rn, self.ru = self.inp(f, "Full Name"), self.inp(f, "Username")
        self.re_, self.rp, self.rc = self.inp(f, "Email"), self.inp(f, "Password", "*"), self.inp(f, "Confirm Password", "*")
        tk.Button(f, text="Register", command=self.register).pack(pady=6)
        tk.Button(f, text="Back to Login", command=self.login_screen).pack()

    def register(self):
        try:
            n, u = self.rn.get().strip(), self.ru.get().strip()
            e, p, p2 = self.re_.get().strip(), self.rp.get(), self.rc.get()
            if not all([n, u, e, p, p2]): messagebox.showwarning("Register", "All fields are required."); return
            if p != p2: messagebox.showwarning("Register", "Passwords do not match."); return
            if "@" not in e or "." not in e.split("@")[-1]: messagebox.showwarning("Register", "Invalid email."); return
            c = db(); c.execute("INSERT INTO users(name,username,email,password) VALUES(?,?,?,?)", (n, u, e, hash_pw(p))); c.commit(); c.close()
            messagebox.showinfo("Register", "Account created! Please login.")
            self.login_screen()
        except sqlite3.IntegrityError: messagebox.showerror("Register", "Username already exists.")
        except Exception as e: messagebox.showerror("Error", f"Registration failed:\n{e}")

    def dashboard(self):
        f = self.screen(f"Welcome, {self.uname}")
        for t, cmd in [("QR Generator", self.qr_screen), ("QR History", self.history_screen),
                       ("Statistics", self.stats), ("Logout", self.logout)]:
            tk.Button(f, text=t, width=25, command=cmd).pack(pady=3)

    def logout(self):
        self.uid = self.uname = None
        self.login_screen()

    def qr_screen(self):
        f = self.screen("QR Generator")
        self.qt = ttk.Combobox(f, values=TYPES, state="readonly"); self.qt.set(TYPES[0]); self.qt.pack(pady=3)
        tk.Label(f, text="Content:").pack(); self.qd = tk.Entry(f, width=45); self.qd.pack(pady=3)
        tk.Button(f, text="Generate QR", command=self.generate).pack(pady=5)
        self.preview = tk.Label(f); self.preview.pack(pady=5)
        tk.Button(f, text="Save QR as PNG", command=self.save).pack(pady=2)
        tk.Button(f, text="Back", command=self.dashboard).pack(pady=4)

    def generate(self):
        try:
            data = self.qd.get().strip()
            if not data: messagebox.showwarning("Input", "Please enter content."); return
            self.img = qrcode.make(data); self.img.thumbnail((220, 220))
            self.preview.image = ImageTk.PhotoImage(self.img); self.preview.config(image=self.preview.image)
            c = db(); c.execute("INSERT INTO qr_codes(user_id,qr_type,content) VALUES(?,?,?)", (self.uid, self.qt.get(), data)); c.commit(); c.close()
            messagebox.showinfo("Success", "QR code generated!")
        except Exception as e: messagebox.showerror("Error", f"Could not generate QR:\n{e}")

    def save(self):
        try:
            if not self.img: messagebox.showwarning("Save", "Generate a QR code first."); return
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if path: self.img.save(path); messagebox.showinfo("Saved", f"QR saved to:\n{path}")
        except Exception as e: messagebox.showerror("Error", f"Could not save QR:\n{e}")

    def history_screen(self):
        f = self.screen("QR History")
        self.tree = ttk.Treeview(f, columns=("ID", "Type", "Content", "Date"), show="headings", height=8)
        self.tree.pack(pady=5)
        tk.Button(f, text="Delete Selected", command=self.delete).pack(pady=3)
        tk.Button(f, text="Back to Dashboard", command=self.dashboard).pack(pady=4)
        self.load()

    def load(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            c = db()
            for r in c.execute("SELECT id,qr_type,content,created_at FROM qr_codes WHERE user_id=?", (self.uid,)):
                self.tree.insert("", "end", values=r)
            c.close()
        except Exception as e: messagebox.showerror("Error", str(e))

    def delete(self):
        try:
            sel = self.tree.selection()
            if not sel: messagebox.showwarning("Delete", "Select a record first."); return
            c = db(); c.execute("DELETE FROM qr_codes WHERE id=? AND user_id=?", (self.tree.item(sel[0], "values")[0], self.uid)); c.commit(); c.close()
            self.load()
        except Exception as e: messagebox.showerror("Error", str(e))

    def stats(self):
        c = db(); d = dict(c.execute("SELECT qr_type,COUNT(*) FROM qr_codes WHERE user_id=? GROUP BY qr_type", (self.uid,)).fetchall()); c.close()
        counts = [d.get(t, 0) for t in TYPES]
        messagebox.showinfo("Statistics", f"Total QR codes: {sum(counts)}\n\n" + "\n".join(f"{t}: {n}" for t, n in zip(TYPES, counts)))

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    QRApp(root)
    root.mainloop()
