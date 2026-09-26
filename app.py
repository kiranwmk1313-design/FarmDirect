from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "farmdirect-demo-secret-key"
DB = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('farmer','buyer')),
        phone TEXT DEFAULT '',
        address TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        description TEXT DEFAULT '',
        location TEXT DEFAULT '',
        FOREIGN KEY(farmer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(buyer_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute("INSERT INTO users(name,email,password,role,phone,address) VALUES (?,?,?,?,?,?)",
                     ("Demo Farmer","farmer@farmdirect.com",generate_password_hash("farmer123"),"farmer","9876543210","Ludhiana, Punjab"))
        conn.execute("INSERT INTO users(name,email,password,role,phone,address) VALUES (?,?,?,?,?,?)",
                     ("Demo Buyer","buyer@farmdirect.com",generate_password_hash("buyer123"),"buyer","9876500000","Ludhiana, Punjab"))
        farmer = conn.execute("SELECT id FROM users WHERE email=?",("farmer@farmdirect.com",)).fetchone()["id"]
        samples = [
            (farmer,"Fresh Tomatoes","Vegetables",40,100,"kg","Farm-fresh red tomatoes.","Ludhiana, Punjab"),
            (farmer,"Basmati Rice","Grains",90,250,"kg","Premium local basmati rice.","Amritsar, Punjab"),
            (farmer,"Organic Wheat","Grains",38,180,"kg","Naturally grown wheat.","Patiala, Punjab"),
            (farmer,"Fresh Potatoes","Vegetables",30,150,"kg","Freshly harvested potatoes.","Moga, Punjab")
        ]
        conn.executemany("INSERT INTO products(farmer_id,name,category,price,quantity,unit,description,location) VALUES (?,?,?,?,?,?,?,?)",samples)
        conn.commit()
    conn.close()

def current_user():
    if "user_id" not in session: return None
    conn=get_db()
    user=conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

@app.route("/")
def index():
    conn=get_db()
    q=request.args.get("q","").strip()
    category=request.args.get("category","").strip()
    sql="SELECT p.*,u.name farmer FROM products p JOIN users u ON u.id=p.farmer_id WHERE p.quantity>0"
    args=[]
    if q: sql+=" AND (p.name LIKE ? OR p.description LIKE ? OR p.location LIKE ?)"; args += [f"%{q}%"]*3
    if category: sql+=" AND p.category=?"; args.append(category)
    sql+=" ORDER BY p.id DESC"
    products=conn.execute(sql,args).fetchall()
    categories=[r["category"] for r in conn.execute("SELECT DISTINCT category FROM products ORDER BY category")]
    conn.close()
    return render_template("index.html", products=products, categories=categories, q=q, category=category)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        password=request.form["password"]; role=request.form["role"]
        if not name or len(password)<6:
            flash("Name is required and password must be at least 6 characters.","danger"); return redirect(url_for("register"))
        conn=get_db()
        try:
            cur=conn.execute("INSERT INTO users(name,email,password,role,phone,address) VALUES(?,?,?,?,?,?)",
                              (name,email,generate_password_hash(password),role,request.form.get("phone",""),request.form.get("address","")))
            conn.commit(); session["user_id"]=cur.lastrowid
            flash("Registration successful.","success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Email is already registered.","danger")
        finally: conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        conn=get_db(); user=conn.execute("SELECT * FROM users WHERE email=?", (request.form["email"].strip().lower(),)).fetchone(); conn.close()
        if user and check_password_hash(user["password"],request.form["password"]):
            session["user_id"]=user["id"]; flash("Welcome back!","success"); return redirect(url_for("dashboard"))
        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); flash("You have been logged out.","success"); return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    user=current_user()
    if not user: return redirect(url_for("login"))
    conn=get_db()
    if user["role"]=="farmer":
        products=conn.execute("SELECT * FROM products WHERE farmer_id=? ORDER BY id DESC",(user["id"],)).fetchall()
        orders=conn.execute("""SELECT o.*,p.name product,b.name buyer FROM orders o JOIN products p ON p.id=o.product_id JOIN users b ON b.id=o.buyer_id WHERE p.farmer_id=? ORDER BY o.id DESC""",(user["id"],)).fetchall()
    else:
        products=[]; orders=conn.execute("""SELECT o.*,p.name product,u.name farmer FROM orders o JOIN products p ON p.id=o.product_id JOIN users u ON u.id=p.farmer_id WHERE o.buyer_id=? ORDER BY o.id DESC""",(user["id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", products=products, orders=orders)

@app.route("/product/<int:pid>")
def product(pid):
    conn=get_db(); p=conn.execute("SELECT p.*,u.name farmer FROM products p JOIN users u ON u.id=p.farmer_id WHERE p.id=?",(pid,)).fetchone(); conn.close()
    if not p: return "Product not found",404
    return render_template("product.html", p=p)

@app.route("/farmer/product/new", methods=["GET","POST"])
def new_product():
    user=current_user()
    if not user or user["role"]!="farmer": return redirect(url_for("login"))
    if request.method=="POST":
        try:
            data=(user["id"],request.form["name"].strip(),request.form["category"],float(request.form["price"]),float(request.form["quantity"]),request.form["unit"],request.form.get("description","").strip(),request.form.get("location","").strip())
            if data[3] < 0 or data[4] < 0: raise ValueError
            conn=get_db(); conn.execute("INSERT INTO products(farmer_id,name,category,price,quantity,unit,description,location) VALUES(?,?,?,?,?,?,?,?)",data); conn.commit(); conn.close()
            flash("Product added successfully.","success"); return redirect(url_for("dashboard"))
        except (ValueError,KeyError):
            flash("Please enter valid product details.","danger")
    return render_template("product_form.html", p=None)

@app.route("/farmer/product/<int:pid>/edit", methods=["GET","POST"])
def edit_product(pid):
    user=current_user()
    if not user or user["role"]!="farmer": return redirect(url_for("login"))
    conn=get_db(); p=conn.execute("SELECT * FROM products WHERE id=? AND farmer_id=?",(pid,user["id"])).fetchone()
    if not p: conn.close(); return "Product not found",404
    if request.method=="POST":
        conn.execute("UPDATE products SET name=?,category=?,price=?,quantity=?,unit=?,description=?,location=? WHERE id=?",
                     (request.form["name"],request.form["category"],float(request.form["price"]),float(request.form["quantity"]),request.form["unit"],request.form.get("description",""),request.form.get("location",""),pid))
        conn.commit(); conn.close(); flash("Product updated.","success"); return redirect(url_for("dashboard"))
    conn.close(); return render_template("product_form.html",p=p)

@app.post("/farmer/product/<int:pid>/delete")
def delete_product(pid):
    user=current_user()
    if not user or user["role"]!="farmer": return redirect(url_for("login"))
    conn=get_db(); conn.execute("DELETE FROM products WHERE id=? AND farmer_id=?",(pid,user["id"])); conn.commit(); conn.close()
    flash("Product deleted.","success"); return redirect(url_for("dashboard"))

@app.post("/order/<int:pid>")
def order(pid):
    user=current_user()
    if not user or user["role"]!="buyer": return redirect(url_for("login"))
    try: qty=float(request.form["quantity"])
    except: qty=0
    conn=get_db(); p=conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    if not p or qty<=0 or qty>p["quantity"]:
        conn.close(); flash("Invalid quantity or insufficient stock.","danger"); return redirect(url_for("product",pid=pid))
    total=qty*p["price"]
    conn.execute("INSERT INTO orders(buyer_id,product_id,quantity,total) VALUES(?,?,?,?)",(user["id"],pid,qty,total))
    conn.execute("UPDATE products SET quantity=quantity-? WHERE id=?",(qty,pid))
    conn.commit(); conn.close(); flash("Order placed successfully.","success"); return redirect(url_for("dashboard"))

@app.post("/order/<int:oid>/status")
def order_status(oid):
    user=current_user()
    if not user or user["role"]!="farmer": return redirect(url_for("login"))
    status=request.form["status"]
    if status not in ("Pending","Accepted","Packed","Delivered","Cancelled"): return redirect(url_for("dashboard"))
    conn=get_db()
    conn.execute("""UPDATE orders SET status=? WHERE id=? AND product_id IN (SELECT id FROM products WHERE farmer_id=?)""",(status,oid,user["id"]))
    conn.commit(); conn.close(); flash("Order status updated.","success"); return redirect(url_for("dashboard"))

@app.route("/profile", methods=["GET","POST"])
def profile():
    user=current_user()
    if not user: return redirect(url_for("login"))
    if request.method=="POST":
        conn=get_db(); conn.execute("UPDATE users SET name=?,phone=?,address=? WHERE id=?",(request.form["name"],request.form.get("phone",""),request.form.get("address",""),user["id"])); conn.commit(); conn.close()
        flash("Profile updated.","success"); return redirect(url_for("profile"))
    return render_template("profile.html", user=user)

if __name__=="__main__":
    init_db()
    app.run(debug=True)
