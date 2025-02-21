import odoorpc
import pandas as pd
from rapidfuzz import process, fuzz
import re
import json


def get_employees():
    """Recupera tutti i dipendenti da Odoo e restituisce una tabella formattata."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    HR_Employee = odoo.env['hr.employee']
    employees = HR_Employee.search_read([], ['name', 'job_title','work_phone','work_email', 'department_id', 'job_id'])

    df = pd.DataFrame(employees)
    
    return df.to_markdown(index=False)
    
def get_department_id(odoo, job_id):
    """Trova il department_id associato al job_id."""
    HR_Job = odoo.env['hr.job']
    job = HR_Job.search_read([('id', '=', job_id)], ['department_id'])
    return job[0]['department_id'] if job else None

def get_parent_id(odoo, department_id):
    """Trova il manager del dipartimento (parent_id)."""
    HR_Department = odoo.env['hr.department']
    department = HR_Department.search_read([('id', '=', department_id)], ['manager_id'])
    return department[0]['manager_id'][0] if department and department[0]['manager_id'] else None

def increment_department_employee_count(odoo, department_id):
    """Incrementa il numero di dipendenti nel dipartimento."""
    HR_job = odoo.env['hr.job']
    department = HR_job.browse(department_id)
    if department:
        department.write({'no_of_employee': department.no_of_employee + 1})


def create_employee(form_data, work_email):
    """Crea un nuovo dipendente in Odoo."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    name = form_data["name"]
    job_title = form_data["job_title"]
    work_phone = form_data["work_phone"]
    job_id = form_data["job_id"]
    resource_calendar = form_data["resource_calendar"]


    # Recupero dei dati mancanti
    department_id = get_department_id(odoo, job_id)
    parent_id = get_parent_id(odoo, department_id[0]) if department_id else None
    coach_id = parent_id  # Il coach è il manager del dipartimento

    HR_Employee = odoo.env['hr.employee']
    employee_id = HR_Employee.create({
        'name': name,
        'job_title': job_title,
        'work_phone': work_phone,
        'work_email': work_email,
        'job_id': job_id,
        'resource_calendar_id': resource_calendar,
        'department_id': department_id[0],
        'work_location_id': 4,
        'parent_id': parent_id,
        'coach_id': coach_id
    })

    # Incrementa il numero di dipendenti nel dipartimento
    if department_id:
        increment_department_employee_count(odoo, department_id[0])

    result = {
        "id": employee_id,
        "name": name,
        "job_title": job_title,
        "work_phone": work_phone,
        "work_email": work_email,
        "job_id": job_id,
        "resource_calendar": resource_calendar,
        "department_id": department_id[0],
        "supervisor_id": parent_id,
        "coach_id": coach_id,
        "link" : f"http://localhost:8069/odoo/org-chart/{employee_id}"
    }

    return result

def get_job_names():
    """Recupera tutti i job da Odoo e restituisce una tabella formattata."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    HR_Job = odoo.env['hr.job']
    jobs = HR_Job.search_read([], ['id','name'])

    df = pd.DataFrame(jobs)
    print("DATAFRAME", df)
    return df.to_markdown(index=False)

def get_resource_calendar():
    """Recupera tutti i job da Odoo e restituisce una tabella formattata."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    HR_Job = odoo.env['resource.calendar']
    jobs = HR_Job.search_read([], ['id','name'])

    df = pd.DataFrame(jobs)
    return df.to_markdown(index=False)

def get_employee_by_name(employee_name):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    Employee = odoo.env['hr.employee']
    
    employees = Employee.search_read([], ['id', 'name'])
    
    if not employees:
        return None
    
    # Lista dei nomi dei prodotti nel database
    employees_names = [employee['name'] for employee in employees]

    # Ricerca fuzzy per trovare i prodotti simili
    matches = process.extract(employee_name, employees_names, scorer=fuzz.ratio, limit=10)  # Prendiamo fino a 10 migliori risultati
    print("MATCHES: ", matches)
    # Controlla se esiste un match con score >= 90
    best_match = next((match[0] for match in matches if match[1] >= 80), None)

    if best_match:
        # Troviamo il prodotto esatto
        matched_employee = next(empl for empl in employees if empl['name'] == best_match)
        return {
            "id": matched_employee["id"],
            "name": matched_employee["name"],
        }
    
    # Se nessun match supera 90, filtra quelli con score > 50
    valid_matches = [match[0] for match in matches if match[1] > 45]

    if not valid_matches:
        return None
    
    # Troviamo i prodotti corrispondenti nel database
    matched_employee = [empl for empl in employees if empl['name'] in valid_matches]
    
    return {
        "multiple_matches": [
            {
            "id": empl["id"], 
            "name": empl["name"]
            }
            for empl in matched_employee
        ]
    }


def is_cv_matching(cv_filename: str, full_name: str, threshold=80) -> bool:
    cv_filename = re.sub(r"[^a-zA-Z]", " ", cv_filename.lower()).strip()  
    full_name = re.sub(r"[^a-zA-Z]", " ", full_name.lower()).strip()
    
    # 2. Tokenizzazione (separa nome e cognome)
    name_parts = full_name.split()  # Divide il nome e cognome

    # 3. Verifica se entrambi i termini sono nel nome del file
    name_match = all(any(fuzz.partial_ratio(part, word) > threshold for word in cv_filename.split()) for part in name_parts)
    
    return name_match

def get_country_id(country, threshold = 85):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    ResCountry = odoo.env['res.country']
    
    countries = ResCountry.search_read([], ['id', 'name'])
    
    if not countries:
        return None
    
    country_names = [country['name'] for country in countries]
    
    # Ricerca fuzzy
    matches = process.extract(country, country_names, scorer=fuzz.ratio, limit=10)
    print("MATCHES:", matches)
    
    # Controlla se esiste un match con score >= threshold
    best_match = next((match[0] for match in matches if match[1] >= threshold), None)
    
    if best_match:
        matched_country = next(c for c in countries if c['name'] == best_match)
        return {
            "id": matched_country["id"],
            "name": matched_country["name"],
        }
    
    # Se nessun match supera threshold, filtra quelli con score > 45
    valid_matches = [match[0] for match in matches if match[1] > 45]
    
    if not valid_matches:
        return None
    
    matched_countries = [c for c in countries if c['name'] in valid_matches]
    
    return {
        "multiple_matches": [
            {
                "id": c["id"], 
                "name": c["name"]
            } for c in matched_countries
        ]
    }


#TODO mettere la tabella completa e far fillare i campi in base al curriculum
def complete_secondary_info(employee, stringa):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    Employee = odoo.env['hr.employee']
    
    emp_id = get_employee_by_name(employee)

    employee_mod = Employee.browse(emp_id['id'])

    data = json.loads(stringa)
    country = data.get("private country", "N/A")
    phone = data.get("mobile phone", "N/A")
    email = data.get("private email", "N/A")
    study_field = data.get("study field", "N/A")
    study_school = data.get("study school", "N/A")
    birthday = data.get("birthday", "N/A")  

    country_name = get_country_id(country)

    employee_mod.write({
        "private_country_id" : country_name['id'],
        "mobile_phone" : phone,
        "private_email" : email,
        "study_field" : study_field,
        "study_school" : study_school,
        "birthday" : birthday
    })

    result = {
        "id": emp_id,
        "name": employee,
        "private country": country_name['name'],
        "private email" : email,
        "study field": study_field,
        "study school" : study_school,
        "birthday" : birthday,
        "link" : f"http://localhost:8069/odoo/employees/{emp_id['id']}"
    }

    return result



def complete_curriculum_info(employee, stringa, threshold=85):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    EmployeeResume = odoo.env['hr.resume.line']
    
    # Trova l'ID del dipendente
    emp_id = get_employee_by_name(employee)
    if not emp_id:
        return {"error": "Employee not found"}
    
    employee_mod = emp_id['id']  # Usa solo l'ID per browse
    print("EMPLOYEE", employee_mod)

    # Decodifica la stringa JSON
    data_list = json.loads(stringa)
    
    # Lista per tenere traccia degli ID creati o aggiornati
    created_entries = []
    
    for data in data_list:
        ist_name = data.get("name", "null")
        description = data.get("description", "null")
        date_start = data.get("date_start", None)  
        date_end = data.get("date_end", None)  
        line_type_id = data.get("line_type_id", "null")
        date_start = date_start if date_start else False
        date_end = date_end if date_end else False

        print(f"Processing entry: {ist_name}, {line_type_id}, {description}")
        
        # Cerca record esistenti senza filtrare per descrizione
        existing_resume = EmployeeResume.search_read([
            ("employee_id", "=", employee_mod),
            ("name", "=", ist_name),
            ("line_type_id", "=", line_type_id)
        ], ["id", "description"])
        
        # Controllo fuzzy sulla descrizione
        best_match = None
        best_score = 0
        for entry in existing_resume:
            plain_description = re.sub(r"<.*?>", "", entry["description"])
            score = fuzz.ratio(description, plain_description)
            print("SCORE", description, "-", plain_description ," ", score)
            if score > best_score:
                best_score = score
                best_match = entry
        # Se il match supera la soglia -> UPDATE
        if best_match and best_score >= threshold:
            print(f"Updating existing record ID {best_match['id']} (similarity {best_score}%)")
            EmployeeResume.browse(best_match["id"]).write({
                "description": description,
                "date_start": date_start,
                "date_end": date_end
            })
            created_entries.append(best_match["id"])
        else:
            # Nessun match simile, creiamo un nuovo record
            print("Creating new record", description)
            new_id = EmployeeResume.create({
                "employee_id": employee_mod,
                "display_type": "classic",
                "name": ist_name if ist_name else None,
                "description": description if description else None,
                "date_start": date_start,
                "date_end": date_end,
                "line_type_id": line_type_id
            })
            created_entries.append(new_id)

    result = {
        "employee_id": emp_id['id'],
        "employee_name": employee,
        "created_entries": created_entries,
        "link": f"http://localhost:8069/odoo/employees/{emp_id['id']}"
    }
    
    return result
