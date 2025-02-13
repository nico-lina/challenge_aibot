import odoorpc
import pandas as pd

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
    return job[0]['department_id'][0] if job else None

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

#TODO trovare il department id -> dal job id
#TODO trovare la work location_id 
#TODO trovare il parent_id in base al department_id
#TODO coach_id = parent_id
def create_employee(name, job_title, work_phone, work_email, job_id, resource_calendar):
    """Crea un nuovo dipendente in Odoo."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Recupero dei dati mancanti
    department_id = get_department_id(odoo, job_id)
    parent_id = get_parent_id(odoo, department_id) if department_id else None
    coach_id = parent_id  # Il coach è il manager del dipartimento

    HR_Employee = odoo.env['hr.employee']
    employee_id = HR_Employee.create({
        'name': name,
        'job_title': job_title,
        'work_phone': work_phone,
        'work_email': work_email,
        'job_id': job_id,
        'resource_calendar_id': resource_calendar,
        'department_id': department_id,
        'work_location_id': 4,
        'parent_id': parent_id,
        'coach_id': coach_id
    })

    # Incrementa il numero di dipendenti nel dipartimento
    if department_id:
        increment_department_employee_count(odoo, department_id)

    result = {
        "id": employee_id,
        "name": name,
        "job_title": job_title,
        "work_phone": work_phone,
        "work_email": work_email,
        "job_id": job_id,
        "resource_calendar": resource_calendar,
        "department_id": department_id,
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