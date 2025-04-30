from flask import render_template, request, redirect, url_for, session
from flask import current_app as app
from .models import Driver
from . import db
from sqlalchemy import text


# ---- Home route ----
@app.route('/')
def home():
    return render_template('login.html')

# ---- Login logic ----
@app.route('/login', methods=['POST'])
def login():
    role = request.form['role']
    identifier = request.form['identifier']

    session['role'] = role
    session['identifier'] = identifier

    if role == 'manager':
        return redirect(url_for('manager_home'))
    elif role == 'client':
        return redirect(url_for('client_home'))
    elif role == 'driver':
        return redirect(url_for('driver_home'))
    else:
        return "Invalid role"

# ---- Manager home ----

@app.route('/manager')
def manager_home():
    return render_template('manager_home.html', identifier=session.get('identifier'))



# ---- Add driver (POST) ----
@app.route('/manager/add_driver', methods=['POST'])
def add_driver():
    name = request.form['name']
    address = request.form['address']

    new_driver = Driver(name=name, address=address)
    db.session.add(new_driver)
    db.session.commit()

    return redirect(url_for('manager_home'))


@app.route('/manager/add_model', methods=['POST'])
def add_model():
    model_name = request.form['model_name']
    num_passengers = int(request.form['num_passengers'])
    car_type = request.form['car_type']

    db.session.execute(
        text("INSERT INTO model (model_name, num_passengers, car_type) VALUES (:mn, :np, :ct)"),
        {"mn": model_name, "np": num_passengers, "ct": car_type}
    )

    db.session.commit()
    return redirect(url_for('manager_home'))

@app.route('/manager/add_car', methods=['POST'])
def add_car():
    car_id = request.form['car_id']
    model_name = request.form['model_name']
    location = request.form['location']

    db.session.execute(
        text("INSERT INTO car (car_id, model_name, current_location) VALUES (:cid, :mn, :loc)"),
        {"cid": car_id, "mn": model_name, "loc": location}
    )
    db.session.commit()
    return redirect(url_for('manager_home'))

@app.route('/manager/top_k_clients', methods=['POST'])
def top_k_clients():
    k = int(request.form['k'])

    query = text("""
        SELECT c.email, COUNT(t.trip_id) as count
        FROM client c
        JOIN trip t ON c.email = t.client_email
        GROUP BY c.email
        ORDER BY count DESC
        LIMIT :k;
    """)

    result = db.session.execute(query, {'k': k})
    top_clients = [{'email': row.email, 'count': row.count} for row in result]

    return render_template('manager_home.html', identifier=session.get('identifier'), top_clients=top_clients)


@app.route('/manager/model_rental_count', methods=['GET'])
def model_rental_count():
    query = text("""
        SELECT car.model_name, COUNT(trip.trip_id) AS rental_count
        FROM trip
        JOIN car ON trip.car_id = car.car_id
        GROUP BY car.model_name
        ORDER BY rental_count DESC;
    """)

    result = db.session.execute(query)
    model_counts = [{'model': row.model_name, 'count': row.rental_count} for row in result]

    return render_template('manager_home.html', identifier=session.get('identifier'), model_counts=model_counts)


@app.route('/manager/driver_stats', methods=['GET'])
def driver_stats():
    query = text("""
        SELECT driver_name, COUNT(*) AS rental_count, ROUND(AVG(rating), 2) AS avg_rating
        FROM trip
        GROUP BY driver_name
        ORDER BY rental_count DESC;
    """)

    result = db.session.execute(query)
    driver_stats = [{'name': row.driver_name, 'count': row.rental_count, 'avg': row.avg_rating} for row in result]

    return render_template('manager_home.html', identifier=session.get('identifier'), driver_stats=driver_stats)


@app.route('/manager/client_driver_pairs', methods=['GET'])
def client_driver_pairs():
    query = text("""
        SELECT start_location, client_email, driver_name
        FROM trip
        ORDER BY start_location, client_email;
    """)

    result = db.session.execute(query)
    city_pairs = [
        {'city': row.start_location, 'client': row.client_email, 'driver': row.driver_name}
        for row in result
    ]

    return render_template('manager_home.html', identifier=session.get('identifier'), city_pairs=city_pairs)

@app.route('/driver', methods=['GET', 'POST'])
def driver_home():
    name = session.get('identifier')
    success = False
    declared = None

    if request.method == 'POST' and 'new_address' in request.form:
        new_address = request.form['new_address']
        db.session.execute(
            text("UPDATE driver SET address = :addr WHERE name = :name"),
            {"addr": new_address, "name": name}
        )
        db.session.commit()
        success = True

    result = db.session.execute(text("SELECT model_name FROM model"))
    model_list = [row.model_name for row in result]

    # 统计租单数 & 平均评分
    stats = db.session.execute(text("""
        SELECT COUNT(*) AS count, ROUND(AVG(rating), 2) AS avg_rating
        FROM trip
        WHERE driver_name = :name
    """), {"name": name}).fetchone()

    trip_count = stats.count
    avg_rating = stats.avg_rating if stats.avg_rating is not None else "N/A"

    return render_template('driver_home.html',
                           name=name,
                           success=success,
                           model_list=model_list,
                           declared=declared,
                           trip_count=trip_count,
                           avg_rating=avg_rating)




@app.route('/driver/update_address', methods=['POST'])
def update_driver_address():
    new_address = request.form['new_address']
    name = session.get('identifier')  

    db.session.execute(
        text("UPDATE driver SET address = :addr WHERE name = :name"),
        {"addr": new_address, "name": name}
    )
    db.session.commit()

    return render_template('driver_home.html', name=name, success=True)


@app.route('/driver/declare_model', methods=['POST'])
def declare_model():
    model_name = request.form['model_name']
    name = session.get('identifier')

    db.session.execute(
        text("INSERT INTO driver_can_drive (driver_name, model_name) VALUES (:name, :model) ON CONFLICT DO NOTHING"),
        {"name": name, "model": model_name}
    )
    db.session.commit()

   
    result = db.session.execute(text("SELECT model_name FROM model"))
    model_list = [row.model_name for row in result]

    return render_template('driver_home.html', name=name, model_list=model_list, declared=model_name)



@app.route('/client/register', methods=['GET', 'POST'])
def client_register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        address = request.form['address']
        credit_card = request.form['credit_card']

        try:
            db.session.execute(
                text("INSERT INTO client (email, name, address, credit_card) VALUES (:e, :n, :a, :c)"),
                {"e": email, "n": name, "a": address, "c": credit_card}
            )
            db.session.commit()
            return render_template('client_register.html', success=True)
        except Exception as e:
            return render_template('client_register.html', error="Email already registered!")

    return render_template('client_register.html')


@app.route('/client/search_models', methods=['POST'])
def search_models():
    date = request.form['date']

    
    query = text("""
        SELECT DISTINCT m.model_name
        FROM model m
        JOIN car c ON m.model_name = c.model_name
        JOIN driver_can_drive dcd ON dcd.model_name = m.model_name
        JOIN driver d ON d.name = dcd.driver_name
        WHERE m.model_name IS NOT NULL
    """)

    result = db.session.execute(query)
    models = [row.model_name for row in result]

    if models:
        return render_template('client_home.html', identifier=session.get('identifier'),
                               results=models, query_date=date)
    else:
        return render_template('client_home.html', identifier=session.get('identifier'),
                               no_result=True, query_date=date)

@app.route('/client')
def client_home():
    return render_template('client_home.html', identifier=session.get('identifier'))



@app.route('/client/rent', methods=['POST'])
def rent_car():
    email = session.get('identifier')
    date = request.form['rental_date']
    model_name = request.form['model_name']
    location = request.form['location']

    # 自动查找一辆可开的车和司机
    query = text("""
        SELECT d.name AS driver_name, c.car_id
        FROM driver d
        JOIN driver_can_drive dcd ON d.name = dcd.driver_name
        JOIN car c ON c.model_name = dcd.model_name
        WHERE dcd.model_name = :model
        LIMIT 1
    """)

    result = db.session.execute(query, {"model": model_name}).fetchone()

    if result:
        driver = result.driver_name
        car_id = result.car_id

        db.session.execute(text("""
            INSERT INTO trip (client_email, driver_name, car_id, start_location, start_time)
            VALUES (:email, :driver, :car, :loc, :time)
        """), {
            "email": email,
            "driver": driver,
            "car": car_id,
            "loc": location,
            "time": date
        })
        db.session.commit()

        return render_template('client_home.html', identifier=email,
                               rent_result={"driver": driver, "car": car_id})
    else:
        return render_template('client_home.html', identifier=email,
                               rent_fail=True)



@app.route('/client/rental_history')
def client_rental_history():
    email = session.get('identifier')

    result = db.session.execute(text("""
        SELECT car_id, driver_name, start_location, start_time, rating
        FROM trip
        WHERE client_email = :email
        ORDER BY start_time DESC;
    """), {"email": email})

    history = []
    for row in result:
        history.append({
            "car": row.car_id,
            "driver": row.driver_name,
            "location": row.start_location,
            "time": row.start_time.strftime('%Y-%m-%d'),
            "rating": row.rating if row.rating is not None else 'N/A'
        })

    return render_template('client_history.html', history=history, identifier=email)


@app.route('/client/review', methods=['GET', 'POST'])
def client_review():
    email = session.get('identifier')

    if request.method == 'POST':
        driver = request.form['driver']
        rating = int(request.form['rating'])

        # 检查是否有过这个司机的 trip
        check = db.session.execute(text("""
            SELECT trip_id FROM trip
            WHERE client_email = :email AND driver_name = :driver
            ORDER BY start_time DESC LIMIT 1
        """), {"email": email, "driver": driver}).fetchone()

        if check:
            trip_id = check.trip_id
            db.session.execute(text("""
                UPDATE trip SET rating = :rating
                WHERE trip_id = :trip_id
            """), {"rating": rating, "trip_id": trip_id})
            db.session.commit()
            return render_template('client_review.html', success=True)
        else:
            return render_template('client_review.html', error=True)

    return render_template('client_review.html')







