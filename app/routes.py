from flask import render_template, request, redirect, url_for, session
from flask import current_app as app
from .models import Driver
from . import db
from sqlalchemy import text

# ---- Home ----
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    role = request.form['role']
    identifier = request.form['identifier']

    
    if role == 'manager':
        result = db.session.execute(
            text("SELECT * FROM manager WHERE ssn = :id"),
            {"id": identifier}
        ).fetchone()
        if not result:
            return render_template('login.html', error="Manager not found.")
    elif role == 'client':
        result = db.session.execute(
            text("SELECT * FROM client WHERE email = :id"),
            {"id": identifier}
        ).fetchone()
        if not result:
            return render_template('login.html', error="Client not found.")
    elif role == 'driver':
        result = db.session.execute(
            text("SELECT * FROM driver WHERE name = :id"),
            {"id": identifier}
        ).fetchone()
        if not result:
            return render_template('login.html', error="Driver not found.")
    else:
        return render_template('login.html', error="Invalid role.")

    
    session['role'] = role
    session['identifier'] = identifier

    if role == 'manager':
        return redirect(url_for('manager_home'))
    elif role == 'client':
        return redirect(url_for('client_home'))
    elif role == 'driver':
        return redirect(url_for('driver_home'))



# ---- Manager_home_page: 4.1,2,3 ----------------------------------------
@app.route('/manager')
def manager_home():
    ssn = session.get('identifier')
    result = db.session.execute(
        text("SELECT name FROM manager WHERE ssn = :ssn"),
        {"ssn": ssn}
    ).fetchone()
    manager_name = result.name if result else "Unknown"
    return render_template('manager_home.html', name=manager_name)


@app.route('/manager/add_driver', methods=['POST'])
def add_driver():
    name = request.form['name']
    road = request.form['road']
    number = request.form['number']
    city = request.form['city']
   
    db.session.execute(
        text("INSERT INTO address (road, number, city) VALUES (:r, :n, :c) ON CONFLICT DO NOTHING"),
        {"r": road, "n": number, "c": city}
    )
    
    db.session.execute(
        text("INSERT INTO driver (name, add_road, add_number, add_city) VALUES (:name, :r, :n, :c)"),
        {"name": name, "r": road, "n": number, "c": city}
    )
    db.session.commit()
    return redirect(url_for('manager_home'))

@app.route('/manager/add_model', methods=['POST'])
def add_model():
    modelid = int(request.form['modelid'])
    carid = int(request.form['carid'])
    color = request.form['color']
    year = int(request.form['year'])
    transmission = request.form['transmission']

    db.session.execute(
        text("""
            INSERT INTO model (modelid, carid, color, year, transmission)
            VALUES (:mid, :cid, :col, :yr, :tran)
        """),
        {"mid": modelid, "cid": carid, "col": color, "yr": year, "tran": transmission}
    )
    db.session.commit()
    return redirect(url_for('manager_home'))

@app.route('/manager/add_car', methods=['POST'])
def add_car():
    carid = int(request.form['carid'])
    brand = request.form['brand']

    db.session.execute(
        text("INSERT INTO car (carid, brand) VALUES (:id, :b)"),
        {"id": carid, "b": brand}
    )
    db.session.commit()
    return redirect(url_for('manager_home'))

@app.route('/manager/delete_model', methods=['POST'])
def delete_model():
    modelid = int(request.form['modelid'])
    carid = int(request.form['carid'])

    try:
        db.session.execute(
            text("DELETE FROM canDrive WHERE modelid = :mid AND carid = :cid"),
            {"mid": modelid, "cid": carid}
        )
        db.session.execute(
            text("DELETE FROM rent WHERE modelid = :mid AND carid = :cid"),
            {"mid": modelid, "cid": carid}
        )
        db.session.execute(
            text("DELETE FROM model WHERE modelid = :mid AND carid = :cid"),
            {"mid": modelid, "cid": carid}
        )
        db.session.commit()
        return redirect(url_for('manager_home'))
    except Exception as e:
        db.session.rollback()
        return f"Failed to delete model: {e}"


@app.route('/manager/delete_car', methods=['POST'])
def delete_car():
    carid = int(request.form['carid'])

    try:
        # must delete model first
        db.session.execute(
            text("DELETE FROM model WHERE carid = :cid"),
            {"cid": carid}
        )
        db.session.execute(
            text("DELETE FROM car WHERE carid = :cid"),
            {"cid": carid}
        )
        db.session.commit()
        return redirect(url_for('manager_home'))
    except Exception as e:
        db.session.rollback()
        return f"Failed to delete car: {e}"


@app.route('/manager/delete_driver', methods=['POST'])
def delete_driver():
    name = request.form['name']

    try:
        
        db.session.execute(text("DELETE FROM review WHERE driver_name = :name"), {"name": name})
        db.session.execute(text("DELETE FROM rent WHERE driver_name = :name"), {"name": name})
        db.session.execute(text("DELETE FROM canDrive WHERE driver_name = :name"), {"name": name})
        db.session.execute(text("DELETE FROM driver WHERE name = :name"), {"name": name})
        db.session.commit()
        return redirect(url_for('manager_home'))
    except Exception as e:
        db.session.rollback()
        return f"Failed to delete driver: {e}"


#--------------------------------------------------------------------------------------------------------------------------------
@app.route('/manager/top_k_clients', methods=['POST'])
def top_k_clients():
    k = int(request.form['k'])

    query = text("""
        SELECT c.name, c.email, COUNT(r.rentid) as count
        FROM client c
        JOIN rent r ON c.email = r.client_email
        GROUP BY c.name, c.email
        ORDER BY count DESC
        LIMIT :k;
    """)

    result = db.session.execute(query, {'k': k})
    top_clients = [{'name': row.name, 'email': row.email, 'count': row.count} for row in result]

    return render_template('manager_home.html', identifier=session.get('identifier'), top_clients=top_clients)

#-------------------------------------------------------------------------------------------------------------------------------------
@app.route('/manager/model_rental_count', methods=['GET'])
def model_rental_count():
    query = text("""
        SELECT m.modelid, COUNT(r.rentid) AS rental_count
        FROM model m
        LEFT JOIN rent r ON m.modelid = r.modelid AND m.carid = r.carid
        GROUP BY m.modelid
        ORDER BY rental_count DESC;
    """)
    result = db.session.execute(query)
    model_counts = [{'model': row.modelid, 'count': row.rental_count} for row in result]

    ssn = session.get("identifier")
    manager_name = db.session.execute(
        text("SELECT name FROM manager WHERE ssn = :ssn"), {"ssn": ssn}
    ).fetchone().name

    return render_template('manager_home.html',
                           identifier=ssn,
                           name=manager_name,
                           model_counts=model_counts)

#-------------------------------------------------------------------------------------------------------------------------------------

@app.route('/manager/driver_stats', methods=['GET'])
def driver_stats():
    query = text("""
        SELECT d.name AS driver_name, 
               COUNT(r.rentid) AS rental_count, 
               ROUND(AVG(rv.rating), 2) AS avg_rating
        FROM driver d
        LEFT JOIN rent r ON d.name = r.driver_name
        LEFT JOIN review rv ON d.name = rv.driver_name AND r.client_email = rv.client_email
        GROUP BY d.name
        ORDER BY rental_count DESC;
    """)

    result = db.session.execute(query)
    driver_stats = [{
        'name': row.driver_name,
        'count': row.rental_count,
        'avg': row.avg_rating if row.avg_rating is not None else "N/A"
    } for row in result]

    ssn = session.get("identifier")
    manager_name = db.session.execute(
        text("SELECT name FROM manager WHERE ssn = :ssn"), {"ssn": ssn}
    ).fetchone().name

    return render_template("manager_home.html",
                           identifier=ssn,
                           name=manager_name,
                           driver_stats=driver_stats)


#-------------------------------------------------------------------------------------------------------------------------------------
@app.route('/manager/city_to_city_clients', methods=['POST'])
def city_to_city_clients():
    city1 = request.form['city1']
    city2 = request.form['city2']

    query = text("""
        SELECT DISTINCT c.name, c.email
        FROM client c
        JOIN locatedAt la ON la.client_email = c.email
        JOIN rent r ON c.email = r.client_email
        JOIN driver d ON d.name = r.driver_name
        WHERE la.city = :city1
          AND (d.add_city = :city2)
    """)

    result = db.session.execute(query, {"city1": city1, "city2": city2})
    matched_clients = [{"name": row.name, "email": row.email} for row in result]

    ssn = session.get("identifier")
    manager_name = db.session.execute(
        text("SELECT name FROM manager WHERE ssn = :ssn"), {"ssn": ssn}
    ).fetchone().name

    return render_template("manager_home.html",
                           identifier=ssn,
                           name=manager_name,
                           matched_clients=matched_clients,
                           city1=city1,
                           city2=city2)



#--------------------------------------------------------------------------------------------------------------------------------
@app.route('/manager/register', methods=['GET', 'POST'])
def register_manager():
    if request.method == 'POST':
        ssn = request.form['ssn']
        name = request.form['name']
        email = request.form['email']

        try:
            db.session.execute(
                text("INSERT INTO manager (ssn, name, email) VALUES (:ssn, :name, :email)"),
                {"ssn": ssn, "name": name, "email": email}
            )
            db.session.commit()
            return render_template('manager_register.html', success=True)
        except:
            return render_template('manager_register.html', error="SSN already registered")

    return render_template('manager_register.html')

#-------------------------------------------------------------------------------------------------------------

@app.route('/driver/update_address', methods=['POST'])
def update_driver_address():
    name = session.get('identifier')
    road = request.form['road']
    number = request.form['number']
    city = request.form['city']

   
    db.session.execute(
        text("""
            INSERT INTO address (road, number, city)
            VALUES (:r, :n, :c)
            ON CONFLICT DO NOTHING
        """), {"r": road, "n": number, "c": city}
    )

    
    db.session.execute(
        text("""
            UPDATE driver
            SET add_road = :r, add_number = :n, add_city = :c
            WHERE name = :name
        """), {"r": road, "n": number, "c": city, "name": name}
    )
    db.session.commit()

    return redirect(url_for('driver_home'))


@app.route('/driver', methods=['GET', 'POST'])
def driver_home():
    name = session.get('identifier')
    success = False
    declared = None

    if request.method == 'POST' and 'new_address' in request.form:
        new_address = request.form['new_address']
        db.session.execute(
            text("UPDATE driver SET add_road = :addr, add_number = '0', add_city = 'Unknown' WHERE name = :name"),
            {"addr": new_address, "name": name}
        )
        db.session.commit()
        success = True

    # 改为使用 modelid
    result = db.session.execute(text("SELECT modelid FROM model"))
    model_list = [row.modelid for row in result]

    stats = db.session.execute(text("""
    SELECT COUNT(*) AS count,
           ROUND(AVG(r.rating), 2) AS avg_rating
    FROM rent t
    LEFT JOIN review r
    ON t.rentid = r.reviewid AND t.driver_name = r.driver_name
    WHERE t.driver_name = :name
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


@app.route('/driver/declare_model', methods=['POST'])
def declare_model():
    modelid = int(request.form['modelid'])
    carid = int(request.form['carid'])
    name = session.get('identifier')

    db.session.execute(
        text("INSERT INTO canDrive (driver_name, modelid, carid) VALUES (:name, :modelid, :carid) ON CONFLICT DO NOTHING"),
        {"name": name, "modelid": modelid, "carid": carid}
    )
    db.session.commit()

    result = db.session.execute(text("SELECT modelid FROM model"))
    model_list = [row.modelid for row in result]

    return render_template('driver_home.html', name=name, model_list=model_list, declared=modelid)


@app.route('/driver/view_models')
def view_models():
    models = db.session.execute(text("""
        SELECT modelid, carid, color, year, transmission
        FROM model
        ORDER BY modelid
    """)).fetchall()

    return render_template('driver_models.html', models=models)




#--------------------------------------------------------------------------------------------------------------
@app.route('/client/register', methods=['GET', 'POST'])
def client_register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        road = request.form['road']
        number = request.form['number']
        city = request.form['city']
        credit_card = request.form['credit_card']

        try:
           
            db.session.execute(
                text("""
                    INSERT INTO address (road, number, city)
                    VALUES (:r, :n, :c)
                    ON CONFLICT DO NOTHING
                """),
                {"r": road, "n": number, "c": city}
            )

            
            db.session.execute(
                text("INSERT INTO client (email, name) VALUES (:e, :n)"),
                {"e": email, "n": name}
            )

            
            db.session.execute(
                text("""
                    INSERT INTO credit (credit_card_number, email, payment_road, payment_number, payment_city)
                    VALUES (:cc, :e, :r, :n, :c)
                """),
                {"cc": credit_card, "e": email, "r": road, "n": number, "c": city}
            )

            
            db.session.execute(
                text("""
                    INSERT INTO locatedAt (client_email, road, number, city)
                    VALUES (:e, :r, :n, :c)
                """),
                {"e": email, "r": road, "n": number, "c": city}
            )

            db.session.commit()
            return render_template('client_register.html', success=True)
        except Exception as e:
            db.session.rollback()
            return render_template('client_register.html', error="Registration failed! Email may already exist.")

    return render_template('client_register.html')



@app.route('/client/search_models', methods=['POST'])
def search_models():
    date = request.form['date']
    email = session.get("identifier")

    
    name_result = db.session.execute(
        text("SELECT name FROM client WHERE email = :email"),
        {"email": email}
    ).fetchone()
    client_name = name_result.name if name_result else "Unknown"

    
    query = text("""
        SELECT DISTINCT m.modelid
        FROM model m
        JOIN car c ON m.carid = c.carid
        JOIN canDrive dcd ON dcd.modelid = m.modelid AND dcd.carid = m.carid
        JOIN driver d ON d.name = dcd.driver_name
        WHERE NOT EXISTS (
            SELECT 1 FROM rent r
            WHERE r.rent_date = :date
              AND (r.modelid = m.modelid AND r.carid = m.carid
                   OR r.driver_name = d.name)
        )
    """)

    result = db.session.execute(query, {"date": date})
    models = [row.modelid for row in result]

    if models:
        return render_template('client_home.html', identifier=email,
                               client_name=client_name, results=models, query_date=date)
    else:
        return render_template('client_home.html', identifier=email,
                               client_name=client_name, no_result=True, query_date=date)



@app.route('/client')
def client_home():
    email = session.get('identifier')
    result = db.session.execute(
        text("SELECT name FROM client WHERE email = :email"),
        {"email": email}
    ).fetchone()
    client_name = result.name if result else "Unknown"
    return render_template('client_home.html', identifier=email, client_name=client_name)


@app.route('/client/rent', methods=['POST'])
def rent_car():
    email = session.get('identifier')
    date = request.form['rental_date']
    modelid = request.form['modelid']

    
    name_result = db.session.execute(
        text("SELECT name FROM client WHERE email = :email"),
        {"email": email}
    ).fetchone()
    client_name = name_result.name if name_result else "Unknown"

    
    query = text("""
    SELECT d.name AS driver_name, c.carid
    FROM driver d
    JOIN canDrive cd ON d.name = cd.driver_name
    JOIN model m ON cd.modelid = m.modelid AND cd.carid = m.carid
    JOIN car c ON c.carid = m.carid
    WHERE cd.modelid = :model
      AND NOT EXISTS (
          SELECT 1 FROM rent r
          WHERE r.rent_date = :date
            AND (r.driver_name = d.name OR r.carid = c.carid)
      )
    LIMIT 1
""")

    result = db.session.execute(query, {"model": modelid, "date": date}).fetchone()


    if result:
        driver = result.driver_name
        car_id = result.carid

      
        db.session.execute(text("""
            INSERT INTO rent (client_email, driver_name, modelid, carid, rent_date)
            VALUES (:email, :driver, :model, :car, :date)
        """), {
            "email": email,
            "driver": driver,
            "model": modelid,
            "car": car_id,
            "date": date
        })

        db.session.commit()

        return render_template('client_home.html', identifier=email, client_name=client_name,
                               rent_result={"driver": driver, "car": car_id})
    else:
        return render_template('client_home.html', identifier=email, client_name=client_name,
                               rent_fail=True)




@app.route('/client/rental_history')
def client_rental_history():
    email = session.get('identifier')

    result = db.session.execute(text("""
        SELECT rent_date, modelid, carid, driver_name
        FROM rent
        WHERE client_email = :email
        ORDER BY rent_date DESC
    """), {"email": email})

    history = [{
        "date": row.rent_date.strftime('%Y-%m-%d'),
        "modelid": row.modelid,
        "carid": row.carid,
        "driver": row.driver_name
    } for row in result]

    return render_template('client_history.html', history=history)




@app.route('/client/review', methods=['GET', 'POST'])
def client_review():
    email = session.get('identifier')

    if request.method == 'POST':
        driver = request.form['driver']
        rating = int(request.form['rating'])
        message = request.form['message']

       
        check = db.session.execute(text("""
            SELECT rentid FROM rent
            WHERE client_email = :email AND driver_name = :driver
            ORDER BY rent_date DESC LIMIT 1
        """), {"email": email, "driver": driver}).fetchone()

        if check:
            reviewid = check.rentid  
            db.session.execute(text("""
                INSERT INTO review (reviewid, driver_name, client_email, rating, message)
                VALUES (:rid, :driver, :email, :rate, :msg)
                ON CONFLICT (reviewid, driver_name)
                DO UPDATE SET rating = EXCLUDED.rating, message = EXCLUDED.message
            """), {
                "rid": reviewid,
                "driver": driver,
                "email": email,
                "rate": rating,
                "msg": message
            })
            db.session.commit()
            return render_template('client_review.html', success=True)
        else:
            return render_template('client_review.html', error=True)

    return render_template('client_review.html')









