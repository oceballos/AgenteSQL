import sqlite3

DB_NAME = "consultorio_psicologia.db"

def run_query(cursor, sql, params=()):
    cursor.execute(sql, params)
    return cursor.fetchall()

def main():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    print("=" * 60)
    print("REPORTE DE VERIFICACIÓN DE BASE DE DATOS DE PSICOLOGÍA")
    print("=" * 60)
    
    # 1. Verificar número de registros por tabla
    print("\n--- 1. Cantidad de Registros por Tabla ---")
    tablas = ["seguros_medicos", "empleados", "pacientes", "agendas", "pagos", "bonificaciones_empleados", "fichas_clinicas"]
    for t in tablas:
        res = run_query(cursor, f"SELECT COUNT(*) FROM {t}")
        print(f"Tabla '{t}': {res[0][0]} registros.")
        
    # 2. Control de Integridad de SQLite (Foreign Keys)
    print("\n--- 2. Comprobación de Integridad de SQLite ---")
    fk_check = run_query(cursor, "PRAGMA foreign_key_check;")
    if not fk_check:
        print("[OK] Sin violaciones de llaves foraneas en la base de datos.")
    else:
        print("[ERROR] Se encontraron violaciones de llaves foraneas:")
        for check in fk_check:
            print(f"  Tabla origen: {check[0]}, RowId: {check[1]}, Tabla referenciada: {check[2]}, FK index: {check[3]}")

    # 3. Consistencia Financiera (Monto paciente + cobertura = Precio base)
    print("\n--- 3. Consistencia Financiera en Pagos ---")
    inconsistencias = run_query(cursor, """
        SELECT p.id, a.id as agenda_id, a.precio_base, p.monto_cobertura, p.monto_paciente
        FROM pagos p
        JOIN agendas a ON p.agenda_id = a.id
        WHERE ABS((p.monto_cobertura + p.monto_paciente) - a.precio_base) > 0.01
    """)
    if not inconsistencias:
        print("[OK] Todos los pagos son consistentes: (monto_cobertura + monto_paciente) = precio_base.")
    else:
        print(f"[ERROR] Se encontraron {len(inconsistencias)} pagos inconsistentes:")
        for inc in inconsistencias[:5]:
            print(f"  Pago ID {inc[0]}: Cita precio base = {inc[2]}, Cobertura = {inc[3]}, Copago Paciente = {inc[4]}")
            
    # 4. Consistencia de Bonificaciones de Empleados
    print("\n--- 4. Validación de Cálculo de Bonificaciones ---")
    # Para validar, recalculamos de forma independiente las bonificaciones esperadas
    # y las comparamos con lo registrado en la tabla bonificaciones_empleados.
    # Regla: comisión por sesión + 150 si total_citas > 30 en el mes.
    inconsistencias_bono = []
    
    cursor.execute("""
        SELECT be.empleado_id, be.mes_anio, be.monto_bono, e.especialidad
        FROM bonificaciones_empleados be
        JOIN empleados e ON be.empleado_id = e.id
    """)
    bonos_registrados = cursor.fetchall()
    
    for emp_id, mes, monto_reg, esp in bonos_registrados:
        # Calcular comisión porcentaje y precio de la especialidad
        # Replicamos el mapeo de especialidades
        precios = {
            "Psicólogo Clínico": (60.0, 0.15),
            "Terapeuta Ocupacional": (70.0, 0.15),
            "Neuropsicólogo": (90.0, 0.20),
            "Psicólogo Infantil": (65.0, 0.15),
            "Terapeuta de Lenguaje": (55.0, 0.12),
            "Psiquiatra": (120.0, 0.25)
        }
        precio_base, porc_com = precios[esp]
        comision_unidad = precio_base * porc_com
        
        # Contar citas 'Realizada' del empleado en ese mes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM agendas 
            WHERE empleado_id = ? AND estado = 'Realizada' AND strftime('%Y-%m', fecha) = ?
        """, (emp_id, mes))
        total_citas = cursor.fetchone()[0]
        
        bono_esperado = round(total_citas * comision_unidad, 2)
        if total_citas > 30:
            bono_esperado += 150.0
            
        if abs(monto_reg - bono_esperado) > 0.01:
            inconsistencias_bono.append((emp_id, mes, monto_reg, bono_esperado))
            
    if not inconsistencias_bono:
        print("[OK] Todos los bonos mensuales coinciden con las citas realizadas e incentivos aplicados.")
    else:
        print(f"[ERROR] Se encontraron {len(inconsistencias_bono)} inconsistencias de bonificaciones:")
        for inc in inconsistencias_bono[:5]:
            print(f"  Empleado {inc[0]} en {inc[1]}: Registrado = {inc[2]}, Calculado = {inc[3]}")
            
    # 5. Consistencia de Fichas Clínicas
    print("\n--- 5. Consistencia de Fichas Clínicas ---")
    inconsistencias_fichas = run_query(cursor, """
        SELECT COUNT(a.id) 
        FROM agendas a 
        LEFT JOIN fichas_clinicas f ON a.id = f.agenda_id 
        WHERE a.estado = 'Realizada' AND f.id IS NULL
    """)[0][0]
    if inconsistencias_fichas == 0:
        print("[OK] Todas las consultas realizadas tienen su correspondiente ficha clinica.")
    else:
        print(f"[ERROR] Se encontraron {inconsistencias_fichas} consultas realizadas sin ficha clinica.")

    # 6. Métricas de Negocio Generales
    print("\n--- 6. Métricas de Operaciones Clínicas ---")
    
    # Recaudación Total
    rec = run_query(cursor, """
        SELECT SUM(monto_paciente), SUM(monto_cobertura), SUM(monto_paciente + monto_cobertura) 
        FROM pagos
    """)[0]
    print(f"Recaudación total en consultas:")
    print(f"  - Copagos recaudados de pacientes: ${rec[0]:,.2f}")
    print(f"  - Recobros a aseguradoras médicas: ${rec[1]:,.2f}")
    print(f"  - Total facturado:                 ${rec[2]:,.2f}")
    
    # Total Bonificaciones pagadas
    bono_total = run_query(cursor, "SELECT SUM(monto_bono) FROM bonificaciones_empleados")[0][0]
    print(f"Total bonificaciones liquidadas a profesionales: ${bono_total:,.2f}")
    
    # Citas por estado
    estados_citas = run_query(cursor, "SELECT estado, COUNT(*) FROM agendas GROUP BY estado")
    print("\nResumen de citas por estado:")
    for est, count in estados_citas:
        print(f"  - {est}: {count}")
        
    # Especialidad más activa (por sesiones completadas)
    esp_activa = run_query(cursor, """
        SELECT e.especialidad, COUNT(a.id) as total_citas
        FROM agendas a
        JOIN empleados e ON a.empleado_id = e.id
        WHERE a.estado = 'Realizada'
        GROUP BY e.especialidad
        ORDER BY total_citas DESC
    """)
    print("\nConsultas realizadas por Especialidad:")
    for esp, cnt in esp_activa:
        print(f"  - {esp}: {cnt} consultas")
        
    # Top 5 terapeutas con más consultas completadas
    top_terapeutas = run_query(cursor, """
        SELECT e.nombre, e.apellido, e.especialidad, COUNT(a.id) as total
        FROM agendas a
        JOIN empleados e ON a.empleado_id = e.id
        WHERE a.estado = 'Realizada'
        GROUP BY e.id
        ORDER BY total DESC
        LIMIT 5
    """)
    print("\nTop 5 Profesionales más Activos:")
    for idx, (nom, ape, esp, total) in enumerate(top_terapeutas, 1):
        print(f"  {idx}. {nom} {ape} ({esp}) - {total} consultas realizadas")
        
    conn.close()
    print("=" * 60)

if __name__ == "__main__":
    main()
