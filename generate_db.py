import sqlite3
import random
import datetime
from datetime import timedelta

# Configuración del archivo de base de datos
DB_NAME = "consultorio_psicologia.db"

# Listas de datos para generación sintética
NOMBRES_MASCULINOS = [
    "Alejandro", "Andrés", "Carlos", "Daniel", "Eduardo", "Francisco", "Gabriel",
    "Hugo", "Javier", "Jorge", "Juan", "Luis", "Manuel", "Mateo", "Nicolás",
    "Pedro", "Roberto", "Santiago", "Sebastián", "Tomás", "Diego", "Felipe",
    "Martin", "Jose", "Fernando", "Ricardo", "Camilo", "Gustavo", "Ángel"
]

NOMBRES_FEMENINOS = [
    "Andrea", "Camila", "Carolina", "Daniela", "Elena", "Gabriela", "Isabel",
    "Josefa", "Laura", "Lucía", "María", "Mariana", "Natalia", "Paula", "Sofía",
    "Valentina", "Valeria", "Verónica", "Victoria", "Beatriz", "Adriana", "Clara",
    "Gloria", "Luisa", "Paola", "Patricia", "Diana", "Sandra", "Monica"
]

APELLIDOS = [
    "Gómez", "Rodríguez", "González", "Fernández", "López", "Díaz", "Martínez",
    "Pérez", "García", "Sánchez", "Romero", "Sosa", "Álvarez", "Torres", "Ruiz",
    "Ramírez", "Flores", "Acosta", "Benítez", "Medina", "Herrera", "Aguirre",
    "Castro", "Ortiz", "Silva", "Toledo", "Mendoza", "Ríos", "Guzmán", "Morales"
]

ESPECIALIDADES = {
    "Psicólogo Clínico": {"precio": 60.0, "comision_porcentaje": 0.15},
    "Terapeuta Ocupacional": {"precio": 70.0, "comision_porcentaje": 0.15},
    "Neuropsicólogo": {"precio": 90.0, "comision_porcentaje": 0.20},
    "Psicólogo Infantil": {"precio": 65.0, "comision_porcentaje": 0.15},
    "Terapeuta de Lenguaje": {"precio": 55.0, "comision_porcentaje": 0.12},
    "Psiquiatra": {"precio": 120.0, "comision_porcentaje": 0.25}
}

SEGUROS_MEDICOS = [
    ("Sanitas", 70.0),
    ("OSDE", 80.0),
    ("Sura", 75.0),
    ("Colpatria", 60.0),
    ("Swiss Medical", 85.0),
    ("Medisalud", 50.0),
    ("Fonasa", 90.0),
    ("Seguro Popular", 40.0)
]

METODOS_PAGO = ["Efectivo", "Tarjeta", "Transferencia"]

def crear_conexion():
    conn = sqlite3.connect(DB_NAME)
    # Habilitar llaves foráneas en SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def crear_tablas(conn):
    cursor = conn.cursor()
    
    # 1. Tabla de Seguros Médicos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seguros_medicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        descuento_porcentaje REAL NOT NULL CHECK(descuento_porcentaje >= 0 AND descuento_porcentaje <= 100)
    );
    """)
    
    # 2. Tabla de Empleados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        especialidad TEXT NOT NULL,
        correo TEXT UNIQUE NOT NULL,
        telefono TEXT,
        fecha_contratacion DATE NOT NULL,
        salario_base REAL NOT NULL CHECK(salario_base >= 0),
        estado TEXT DEFAULT 'Activo' CHECK(estado IN ('Activo', 'Inactivo'))
    );
    """)
    
    # 3. Tabla de Pacientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        fecha_nacimiento DATE NOT NULL,
        genero TEXT CHECK(genero IN ('M', 'F', 'Otro')),
        correo TEXT UNIQUE,
        telefono TEXT,
        seguro_id INTEGER,
        fecha_registro DATE NOT NULL,
        FOREIGN KEY (seguro_id) REFERENCES seguros_medicos(id) ON DELETE SET NULL
    );
    """)
    
    # 4. Tabla de Agendas (Consultas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER NOT NULL,
        paciente_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        hora TEXT NOT NULL,
        estado TEXT DEFAULT 'Programada' CHECK(estado IN ('Programada', 'Realizada', 'Cancelada', 'No Asistió')),
        precio_base REAL NOT NULL CHECK(precio_base >= 0),
        notas TEXT,
        FOREIGN KEY (empleado_id) REFERENCES empleados(id),
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        UNIQUE(empleado_id, fecha, hora)  -- Previene cruce de horarios para el mismo terapeuta
    );
    """)
    
    # 5. Tabla de Pagos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agenda_id INTEGER UNIQUE NOT NULL,
        fecha_pago DATE NOT NULL,
        monto_cobertura REAL NOT NULL CHECK(monto_cobertura >= 0),
        monto_paciente REAL NOT NULL CHECK(monto_paciente >= 0),
        metodo_pago TEXT NOT NULL CHECK(metodo_pago IN ('Efectivo', 'Tarjeta', 'Transferencia', 'Seguro')),
        estado_pago TEXT DEFAULT 'Completado' CHECK(estado_pago IN ('Pendiente', 'Completado', 'Reembolsado')),
        FOREIGN KEY (agenda_id) REFERENCES agendas(id)
    );
    """)
    
    # 6. Tabla de Bonificaciones de Empleados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bonificaciones_empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER NOT NULL,
        mes_anio TEXT NOT NULL, -- Formato 'YYYY-MM'
        monto_bono REAL NOT NULL CHECK(monto_bono >= 0),
        criterio TEXT NOT NULL,
        fecha_pago_bono DATE,
        FOREIGN KEY (empleado_id) REFERENCES empleados(id),
        UNIQUE(empleado_id, mes_anio) -- Una liquidación de bono por empleado al mes
    );
    """)
    
    # Crear Índices para optimizar el rendimiento
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_empleados_especialidad ON empleados(especialidad);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pacientes_seguro ON pacientes(seguro_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agendas_empleado_fecha ON agendas(empleado_id, fecha);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agendas_paciente_fecha ON agendas(paciente_id, fecha);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pagos_agenda ON pagos(agenda_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bonificaciones_empleado ON bonificaciones_empleados(empleado_id);")
    
    conn.commit()
    print("Esquema de base de datos e índices creados exitosamente.")

def generar_datos_sinteticos(conn):
    cursor = conn.cursor()
    random.seed(42)  # Para reproducibilidad de los datos sintéticos
    
    # --- 1. Insertar Seguros Médicos ---
    seguros_ids = []
    for nombre, desc in SEGUROS_MEDICOS:
        cursor.execute(
            "INSERT INTO seguros_medicos (nombre, descuento_porcentaje) VALUES (?, ?)",
            (nombre, desc)
        )
        seguros_ids.append(cursor.lastrowid)
    # Añadimos None para representar particulares (sin seguro)
    seguros_ids.append(None)
    
    # --- 2. Insertar Empleados ---
    empleados_list = []
    # Generamos 25 empleados profesionales
    for i in range(25):
        genero = random.choice(['M', 'F'])
        nombre = random.choice(NOMBRES_MASCULINOS if genero == 'M' else NOMBRES_FEMENINOS)
        apellido1 = random.choice(APELLIDOS)
        apellido2 = random.choice(APELLIDOS)
        apellido = f"{apellido1} {apellido2}"
        
        especialidad = random.choice(list(ESPECIALIDADES.keys()))
        correo = f"{nombre.lower()}.{apellido1.lower()}@clinica-mente.com"
        
        # Asegurar correo único agregando número si es necesario
        intentos = 1
        while True:
            cursor.execute("SELECT 1 FROM empleados WHERE correo = ?", (correo,))
            if not cursor.fetchone():
                break
            correo = f"{nombre.lower()}.{apellido1.lower()}{intentos}@clinica-mente.com"
            intentos += 1
            
        telefono = f"+57 3{random.randint(10, 19)} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        
        # Fecha de contratación entre hace 5 años y hace 6 meses
        dias_atras = random.randint(180, 5 * 365)
        fecha_contratacion = (datetime.date(2026, 6, 21) - timedelta(days=dias_atras)).isoformat()
        
        # Salarios base realistas
        salarios_base = {
            "Psicólogo Clínico": 2500.0,
            "Terapeuta Ocupacional": 2700.0,
            "Neuropsicólogo": 3500.0,
            "Psicólogo Infantil": 2600.0,
            "Terapeuta de Lenguaje": 2400.0,
            "Psiquiatra": 4500.0
        }
        salario = salarios_base[especialidad] + random.randint(-200, 500)
        estado = 'Activo' if random.random() < 0.9 else 'Inactivo'
        
        cursor.execute("""
            INSERT INTO empleados (nombre, apellido, especialidad, correo, telefono, fecha_contratacion, salario_base, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, apellido, especialidad, correo, telefono, fecha_contratacion, salario, estado))
        
        empleados_list.append({
            "id": cursor.lastrowid,
            "especialidad": especialidad,
            "fecha_contratacion": datetime.date.fromisoformat(fecha_contratacion),
            "estado": estado
        })
        
    # --- 3. Insertar Pacientes ---
    pacientes_list = []
    # Generamos 350 pacientes
    for i in range(350):
        genero = random.choice(['M', 'F', 'Otro'])
        if genero == 'M':
            nombre = random.choice(NOMBRES_MASCULINOS)
        elif genero == 'F':
            nombre = random.choice(NOMBRES_FEMENINOS)
        else:
            nombre = random.choice(NOMBRES_MASCULINOS + NOMBRES_FEMENINOS)
            
        apellido1 = random.choice(APELLIDOS)
        apellido2 = random.choice(APELLIDOS)
        apellido = f"{apellido1} {apellido2}"
        
        # Edad entre 5 y 80 años
        edad_dias = random.randint(5 * 365, 80 * 365)
        fecha_nacimiento = (datetime.date(2026, 6, 21) - timedelta(days=edad_dias)).isoformat()
        
        correo = f"{nombre.lower()}.{apellido1.lower()}{random.randint(10, 999)}@gmail.com"
        telefono = f"+57 3{random.randint(0, 9)}{random.randint(0, 9)} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        
        # Seguro médico (alrededor del 70% de probabilidad de tener uno)
        seguro_id = random.choice(seguros_ids) if random.random() < 0.70 else None
        
        # Fecha de registro
        fecha_reg = (datetime.date(2026, 6, 21) - timedelta(days=random.randint(30, 730))).isoformat()
        
        cursor.execute("""
            INSERT INTO pacientes (nombre, apellido, fecha_nacimiento, genero, correo, telefono, seguro_id, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, apellido, fecha_nacimiento, genero, correo, telefono, seguro_id, fecha_reg))
        
        pacientes_list.append({
            "id": cursor.lastrowid,
            "seguro_id": seguro_id,
            "fecha_registro": datetime.date.fromisoformat(fecha_reg)
        })
        
    # --- 4. Generar Agendas (Citas) ---
    print("Generando agendas de consultas...")
    
    # Rango de fechas: Desde el 2025-06-01 hasta el 2026-08-31
    fecha_inicio = datetime.date(2025, 6, 1)
    fecha_fin = datetime.date(2026, 8, 31)
    delta_total = (fecha_fin - fecha_inicio).days
    
    HORARIOS = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    
    agendas_registradas = []
    
    # Para evitar colisiones en sqlite y simplificar, recorremos día a día
    # y asignamos citas a los empleados activos.
    curr_date = fecha_inicio
    fecha_hoy = datetime.date(2026, 6, 21) # Fecha actual de simulación
    
    while curr_date <= fecha_fin:
        # No trabajamos domingos
        if curr_date.weekday() == 6:
            curr_date += timedelta(days=1)
            continue
            
        # Sábados a medio día
        horarios_dia = HORARIOS[:4] if curr_date.weekday() == 5 else HORARIOS
        
        # Cada empleado activo tiene una probabilidad de atender citas este día
        for emp in empleados_list:
            if emp["estado"] == "Inactivo" or emp["fecha_contratacion"] > curr_date:
                continue
                
            # Probabilidad de tener agenda este día
            prob_agenda = 0.85 if curr_date.weekday() < 5 else 0.40
            if random.random() > prob_agenda:
                continue
                
            # Determinar cuántas citas atiende (1 a 5 citas)
            num_citas = random.randint(1, min(5, len(horarios_dia)))
            horas_seleccionadas = random.sample(horarios_dia, num_citas)
            
            for hora in horas_seleccionadas:
                # Seleccionar un paciente registrado antes de la fecha de la cita
                pacientes_elegibles = [p for p in pacientes_list if p["fecha_registro"] <= curr_date]
                if not pacientes_elegibles:
                    continue
                
                paciente = random.choice(pacientes_elegibles)
                
                # Estado de la cita basado en la fecha de la cita con respecto a la fecha actual (hoy)
                if curr_date < fecha_hoy:
                    # En el pasado: Realizada, Cancelada, No asistió
                    r = random.random()
                    if r < 0.82:
                        estado = 'Realizada'
                    elif r < 0.94:
                        estado = 'Cancelada'
                    else:
                        estado = 'No Asistió'
                else:
                    # En el futuro o hoy: Programada
                    estado = 'Programada'
                    
                # Precio base de la especialidad
                esp_info = ESPECIALIDADES[emp["especialidad"]]
                precio = esp_info["precio"]
                
                notas = ""
                if estado == 'Realizada':
                    notas = random.choice([
                        "Paciente muestra mejoría en el estado de ánimo.",
                        "Sesión enfocada en técnicas de relajación y respiración.",
                        "Se revisan tareas asignadas la semana anterior.",
                        "Se evidencia avance en el control de impulsos.",
                        "Se realiza evaluación diagnóstica preliminar.",
                        "Dificultades reportadas en el entorno familiar. Sesión constructiva.",
                        "Excelente recepción a las dinámicas de juego (terapia infantil).",
                        "Seguimiento de rutina sin novedades mayores."
                    ])
                elif estado == 'Cancelada':
                    notas = random.choice([
                        "Paciente cancela con 24h de anticipación por motivos laborales.",
                        "Cancelado por enfermedad del paciente.",
                        "Terapéuta cancela por cruce de congreso médico.",
                        "Cancelada a última hora por problemas de movilidad."
                    ])
                elif estado == 'No Asistió':
                    notas = "No se presentó ni avisó previamente."
                
                cursor.execute("""
                    INSERT INTO agendas (empleado_id, paciente_id, fecha, hora, estado, precio_base, notas)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (emp["id"], paciente["id"], curr_date.isoformat(), hora, estado, precio, notas))
                
                agenda_id = cursor.lastrowid
                agendas_registradas.append({
                    "id": agenda_id,
                    "empleado_id": emp["id"],
                    "paciente_id": paciente["id"],
                    "fecha": curr_date,
                    "estado": estado,
                    "precio_base": precio,
                    "seguro_id": paciente["seguro_id"]
                })
                
        curr_date += timedelta(days=1)
        
    print(f"Total de citas generadas: {len(agendas_registradas)}")
    
    # --- 5. Generar Pagos ---
    print("Generando transacciones de pagos...")
    
    # Mapeo de porcentajes de descuento por seguro
    cursor.execute("SELECT id, descuento_porcentaje FROM seguros_medicos")
    descuentos_seguro = {row[0]: row[1] for row in cursor.fetchall()}
    
    pago_count = 0
    for cita in agendas_registradas:
        # Solo se pagan las citas 'Realizadas' (o algunas clínicas cobran cargos de cancelación, pero para simpleza, solo Realizadas)
        if cita["estado"] != 'Realizada':
            continue
            
        seg_id = cita["seguro_id"]
        precio_base = cita["precio_base"]
        
        if seg_id is not None and seg_id in descuentos_seguro:
            desc_porc = descuentos_seguro[seg_id]
            monto_cobertura = round(precio_base * (desc_porc / 100.0), 2)
            monto_paciente = round(precio_base - monto_cobertura, 2)
            metodo = 'Seguro' if monto_paciente == 0 else random.choice(METODOS_PAGO)
        else:
            monto_cobertura = 0.0
            monto_paciente = precio_base
            metodo = random.choice(METODOS_PAGO)
            
        # Fecha de pago: mismo día de la cita o 1-2 días después
        dias_retraso = random.choice([0, 0, 0, 1, 2])
        fecha_p = (cita["fecha"] + timedelta(days=dias_retraso)).isoformat()
        
        cursor.execute("""
            INSERT INTO pagos (agenda_id, fecha_pago, monto_cobertura, monto_paciente, metodo_pago, estado_pago)
            VALUES (?, ?, ?, ?, ?, 'Completado')
        """, (cita["id"], fecha_p, monto_cobertura, monto_paciente, metodo))
        pago_count += 1
        
    print(f"Total de pagos procesados: {pago_count}")
    
    # --- 6. Generar Bonificaciones de Empleados ---
    print("Calculando y generando bonificaciones de empleados...")
    
    # Vamos a calcular bonificaciones de forma mensual, desde Junio 2025 hasta Mayo 2026 (meses cerrados)
    meses_analisis = []
    # Generar lista de YYYY-MM
    for y in [2025]:
        for m in range(6, 13):
            meses_analisis.append(f"{y}-{m:02d}")
    for y in [2026]:
        for m in range(1, 6): # Enero a Mayo (Junio está en curso)
            meses_analisis.append(f"{y}-{m:02d}")
            
    bonos_count = 0
    for mes in meses_analisis:
        # Obtener consultas completadas por cada empleado en este mes
        # Usamos SQL para agrupar
        cursor.execute("""
            SELECT empleado_id, COUNT(id) as total_citas
            FROM agendas
            WHERE estado = 'Realizada' AND strftime('%Y-%m', fecha) = ?
            GROUP BY empleado_id
        """, (mes,))
        
        rendimientos = cursor.fetchall()
        for emp_id, total_citas in rendimientos:
            # Obtener comisión según la especialidad del empleado
            emp_info = next((e for e in empleados_list if e["id"] == emp_id), None)
            if not emp_info:
                continue
                
            esp_info = ESPECIALIDADES[emp_info["especialidad"]]
            comision_sesion = esp_info["precio"] * esp_info["comision_porcentaje"]
            
            # Bono base de comisiones por sesión completada
            bono_acumulado = round(total_citas * comision_sesion, 2)
            criterio = f"Comisión del {int(esp_info['comision_porcentaje']*100)}% por {total_citas} consultas realizadas"
            
            # Super bonificación por alto volumen: si hace más de 30 consultas
            if total_citas > 30:
                bono_extra = 150.0
                bono_acumulado += bono_extra
                criterio += f" + Bono de desempeño por alto volumen (${bono_extra})"
                
            # Fecha de pago del bono: el día 5 del mes siguiente
            anio_act, mes_act = map(int, mes.split('-'))
            if mes_act == 12:
                mes_sig = 1
                anio_sig = anio_act + 1
            else:
                mes_sig = mes_act + 1
                anio_sig = anio_act
                
            fecha_pago_bono = datetime.date(anio_sig, mes_sig, 5).isoformat()
            
            cursor.execute("""
                INSERT INTO bonificaciones_empleados (empleado_id, mes_anio, monto_bono, criterio, fecha_pago_bono)
                VALUES (?, ?, ?, ?, ?)
            """, (emp_id, mes, bono_acumulado, criterio, fecha_pago_bono))
            bonos_count += 1
            
    print(f"Total de bonificaciones liquidadas: {bonos_count}")
    conn.commit()

def main():
    print(f"Iniciando creación de base de datos {DB_NAME}...")
    conn = crear_conexion()
    try:
        crear_tablas(conn)
        generar_datos_sinteticos(conn)
        print("\n¡Proceso finalizado con éxito!")
        print("La base de datos SQLite 'consultorio_psicologia.db' ha sido generada.")
    except Exception as e:
        print(f"Error durante la generación: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
