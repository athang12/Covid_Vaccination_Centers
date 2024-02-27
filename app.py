from flask import Flask,request,render_template,redirect,url_for, jsonify;
from flask_login import  LoginManager,UserMixin, login_user,login_required,logout_user,current_user
from flask_mysqldb import  MySQL
from flask_bcrypt import  Bcrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env.

app = Flask( __name__ )
app.secret_key='mysecretkey'

app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "Athang33!"
app.config['MYSQL_DB'] = "flask_db"

mysql = MySQL(app)
login_manager = LoginManager()
login_manager.init_app(app)
bcrypt = Bcrypt(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id);

class User(UserMixin):
    def __init__ (self,user_id,name,email):
        self.id = user_id
        self.name = name
        self.email = email
    

    @staticmethod
    def get(user_id):
        cursor = mysql.connection.cursor()   
        cursor.execute("SELECT name,email from users where id = %s",(user_id))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return User(user_id,result[0],result[1])

def notify_clients():
    # You may need to adapt this to your specific web framework or server setup
    # For example, using Flask's jsonify to send a response to the client
    response_data = {"reload_page": True}
    return jsonify(response_data)

def reset_slots_if_needed():
    cur = mysql.connection.cursor()
    cur.execute('SELECT id, last_reset FROM vaccination_centers')
    centers = cur.fetchall()
    current_time = datetime.utcnow()

    for center in centers:
        center_id, last_reset = center[0], center[1]
        time_difference = current_time - last_reset
        if time_difference.total_seconds() > 86400:  # 1 day has 864000 seconds
            cur.execute('UPDATE vaccination_centers SET available_slots = 10, last_reset = %s WHERE id = %s',
                        (current_time, center_id))
            mysql.connection.commit()

    cur.close()
    notify_clients()



@app.route("/")
def index():
    return render_template('homepage.html')

@app.route('/userlogin', methods = ['GET', 'POST'])
def userlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']


        cursor = mysql.connection.cursor()   
        cursor.execute('SELECT id,name,email,password from users where email = %s',(email,))
        user_data = cursor.fetchone()
        cursor.close()

        if user_data and bcrypt.check_password_hash(user_data[3],password):
            user = User(user_data[0],user_data[1],user_data[2])
            login_user(user)
            return redirect(url_for('userdashboard')) 

    return render_template('userlogin.html')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        # print(os.getenv("PASSWORD"))
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()   
        cursor.execute("INSERT INTO users (name,email,password) values (%s,%s,%s)",(name,email,hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('userlogin'))
        
    return render_template('register.html')

@app.route('/userdashboard', methods = ['GET', 'POST'])
@login_required
def userdashboard():
    reset_slots_if_needed();
    if current_user.is_authenticated:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM vaccination_centers')
        centers = cur.fetchall()
        cur.close()
        # print(centers)
        return render_template('dashboard.html',centers=centers)
    else:
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admindashboard', methods = ['GET', 'POST'])
@login_required
def admindashboard():
    reset_slots_if_needed();
    if current_user.is_authenticated:
        reset_slots_if_needed()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM vaccination_centers')
        centers = cur.fetchall()
        cur.close()
        return render_template('index.html') 
    else:
        return redirect(url_for('index'))

@app.route('/search', methods=['POST'])
def search():
    reset_slots_if_needed();
    if request.method == 'POST':
        reset_slots_if_needed()
        search_term = request.form['search_term']
        cur = mysql.connection.cursor()
        if not search_term.strip():  # Check if search_term is empty or contains only whitespace
            cur.execute('SELECT * FROM vaccination_centers')
        else:
            # Use LOWER() to make the search case-insensitive
            cur.execute('SELECT * FROM vaccination_centers WHERE LOWER(name) LIKE LOWER(%s)', ('%' + search_term + '%',))

        centers = cur.fetchall()
        cur.close()
        return render_template('dashboard.html', centers=centers)
    
    


@app.route('/apply/<int:center_id>', methods=['GET', 'POST'])
def apply(center_id):
    reset_slots_if_needed()
    cur = mysql.connection.cursor(dictionary=True)
    cur.execute('SELECT * FROM vaccination_centers WHERE id = %s', (center_id,))
    center = cur.fetchone()

    if request.method == 'POST':
        if center['available_slots'] > 0:
            cur.execute('UPDATE vaccination_centers SET available_slots = available_slots - 1 WHERE id = %s', (center_id,))
            mysql.connection.commit()
            return redirect(url_for('index'))

    cur.close()
    return render_template('apply.html', center=center)

@app.route('/add', methods=['GET', 'POST'])
def add():
    reset_slots_if_needed()
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        working_hours = request.form['working_hours']

        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO vaccination_centers (name, address, working_hours, available_slots, last_reset) VALUES (%s, %s, %s, 10, %s)',
                    (name, address, working_hours, datetime.utcnow()))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('admindashboard'))

    return render_template('add.html')

@app.route('/adminlogin', methods = ['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']


        cursor = mysql.connection.cursor()   
        cursor.execute('SELECT id,name,email,password from admindb where email = %s',(email,))
        user_data = cursor.fetchone()
        cursor.close()

        if user_data and bcrypt.check_password_hash(user_data[3],password):
            user = User(user_data[0],user_data[1],user_data[2])
            login_user(user)
            return redirect(url_for('admindashboard')) 

    return render_template('adminlogin.html')

@app.route('/apply_slot', methods=['POST'])
def apply_slot():
    reset_slots_if_needed();
    data = request.get_json()
    hospital_name = data.get('hospitalName')

    cur = mysql.connection.cursor()
    
    # Check if slots are available
    cur.execute('SELECT available_slots FROM vaccination_centers WHERE name = %s', (hospital_name,))
    available_slots = cur.fetchone()[0]

    if available_slots > 0:
        # Update the slots in the database
        cur.execute('UPDATE vaccination_centers SET available_slots = available_slots - 1 WHERE name = %s', (hospital_name,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Successfully booked a slot at ' + hospital_name})
    else:
        cur.close()
        return jsonify({'success': False, 'message': 'No slots available at ' + hospital_name})

@app.route('/dosagedetails', methods = ['GET', 'POST'])
@login_required
def dosagedetails():
    reset_slots_if_needed();
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM vaccination_centers')
    centers = cur.fetchall()
    cur.close()
    # print(centers)
    return render_template('dosage.html',centers=centers)

@app.route('/removehospitals', methods = ['GET', 'POST'])
@login_required
def removehospitals():
    reset_slots_if_needed();
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM vaccination_centers')
    centers = cur.fetchall()
    cur.close()
    # print(centers)
    return render_template('remove.html',centers=centers)    

@app.route('/remove/<int:center_id>', methods=['GET'])
def remove_hospital(center_id):
    cur = mysql.connection.cursor()

    # Check if the hospital exists
    cur.execute('SELECT name FROM vaccination_centers WHERE id = %s', (center_id,))
    hospital_name = cur.fetchone()

    if hospital_name:
        # Remove the hospital from the database
        cur.execute('DELETE FROM vaccination_centers WHERE id = %s', (center_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Successfully removed ' + hospital_name[0]})
    else:
        cur.close()
        return jsonify({'success': False, 'message': 'Hospital not found'})

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
# 12345
