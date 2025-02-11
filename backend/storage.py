import mysql.connector
from mysql.connector import Error

#  Conexión a la base de datos
def get_db():
     connection = None
     try:
         # Conectamos a la base de datos
         connection = mysql.connector.connect(
             host="127.0.0.1",
             user="root",
             password="",
             database="db_gdocumental"
         )
     except Error as e:
         print(f"Error: '{e}'")
     return connection



# RUTAS DE USUARIOS - CRUD 


def get_user(str_name_user: str, str_password: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener el id, usuario, correo, contraseña, permisos y área
    query = """
        SELECT id, str_name_user, str_email, str_password, id_permission, id_area
        FROM tbl_users
        WHERE str_name_user = %s
    """

    # Ejecutar la consulta
    cursor.execute(query, (str_name_user,))
    user = cursor.fetchone()

    # Cerrar conexión
    cursor.close()
    connection.close()

    # Verificar si el usuario existe y si la contraseña coincide
    if user and str_password == user['str_password']:
        # Retornar datos completos del usuario, incluyendo el "id"
        return {
            "id": user["id"],
            "username": user["str_name_user"],
            "email": user["str_email"],
            "id_permission": user["id_permission"],
            "id_area": user["id_area"],
        }

    # Retornar None si la validación falla
    return None


# Función para obtener los usuarios desde la base de datos
def get_users():
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener los usuarios
    query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
    """
    cursor.execute(query)
    users = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    connection.close()

    return users


    
def delete_user(user_id):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # Verificar si el usuario existe
        check_query = "SELECT id FROM tbl_users WHERE id = %s"
        cursor.execute(check_query, (user_id,))
        user = cursor.fetchone()  # Si existe, fetchone devolverá el usuario

        if not user:  # Si no existe el usuario
            print(f"Usuario con ID {user_id} no encontrado.")
            return False  # Usuario no encontrado

        # Si el usuario existe, proceder a eliminarlo
        query = "DELETE FROM tbl_users WHERE id = %s"
        cursor.execute(query, (user_id,))
        connection.commit()  # Confirmar los cambios
        success = cursor.rowcount > 0  # Verificar si se eliminó el usuario
        return success  # Retorna True si se eliminó, False si no

    except Exception as e:
        connection.rollback()  # Revertir en caso de error
        print(f"Error al eliminar el usuario: {e}")
        return False

    finally:
        cursor.close()  # Cerrar el cursor
        connection.close()  # Cerrar la conexión



# Función para agregar un usuario a la base de datos
def add_user(str_name_user: str, str_email: str, str_password: str, id_permission: int, id_area: int):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # Verificar si el usuario ya existe
        query_check = "SELECT id FROM tbl_users WHERE str_name_user = %s"
        cursor.execute(query_check, (str_name_user,))
        existing_user = cursor.fetchone()

        if existing_user:
            return {"success": False, "message": "El usuario ya existe"}

        # Insertar nuevo usuario
        query_insert = """
            INSERT INTO tbl_users (str_name_user, str_email, str_password, id_permission, id_area)
            VALUES (%s, %s, %s, %s, %s) 
        """
        cursor.execute(query_insert, (str_name_user, str_email, str_password, id_permission, id_area))
        connection.commit()

        return {"success": True, "message": "Usuario creado correctamente"}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

    finally:
        cursor.close()
        connection.close()

# Función para actualizar el usuario en la base de datos
def update_user(id: int, str_name_user: str, str_email: str, str_password: str, id_permission: int, id_area: int):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # Verificar si el usuario existe
        query_check = "SELECT id FROM tbl_users WHERE id = %s"
        cursor.execute(query_check, (id,))
        existing_user = cursor.fetchone()

        if not existing_user:
            return {"success": False, "message": "Usuario no encontrado"}

        # Actualizar los datos del usuario
        query_update = """
            UPDATE tbl_users
            SET str_name_user = %s, str_email = %s, str_password = %s, id_permission = %s, id_area = %s
            WHERE id = %s
        """
        cursor.execute(query_update, (str_name_user, str_email, str_password, id_permission, id_area, id))
        connection.commit()

        return {"success": True, "message": "Usuario actualizado correctamente"}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

    finally:
        cursor.close()
        connection.close()




# RUTAS DE AREAS - CRUD 


# Función para obtener los usuarios desde la base de datos
def get_areas():
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener los usuarios
    query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
    """
    cursor.execute(query)
    areas = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    connection.close()

    return areas


# Función para agregar un area a la base de datos
def add_area(str_name_area: str, str_description: str):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # Verificar si el usuario ya existe
        query_check = "SELECT id FROM tbl_areas WHERE str_name_area = %s"
        cursor.execute(query_check, (str_name_area,))
        existing_area = cursor.fetchone()

        if existing_area:
            return {"success": False, "message": "El area ya existe"}

        # Insertar nuevo usuario
        query_insert = """
            INSERT INTO tbl_areas (str_name_area, str_description)
            VALUES (%s, %s) 
        """
        cursor.execute(query_insert, (str_name_area, str_description))
        connection.commit()

        return {"success": True, "message": "Area creada correctamente"}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

    finally:
        cursor.close()
        connection.close()

# Función para actualizar el usuario en la base de datos
def update_area(id: int, str_name_area: str, str_description: str):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # Verificar si el usuario existe
        query_check = "SELECT id FROM tbl_areas WHERE id = %s"
        cursor.execute(query_check, (id,))
        existing_area = cursor.fetchone()

        if not existing_area:
            return {"success": False, "message": "Area no encontrado"}

        # Actualizar los datos del area
        query_update = """
            UPDATE tbl_areas
            SET str_name_area = %s, str_description = %s
            WHERE id = %s
        """
        cursor.execute(query_update, (str_name_area,str_description, id))
        connection.commit()

        return {"success": True, "message": "Area actualizado correctamente"}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

    finally:
        cursor.close()
        connection.close()

def delete_area(area_id):
    connection = get_db()
    cursor = connection.cursor()

    try:
        # 1. Verificar que el área exista en tbl_areas
        check_query = "SELECT id FROM tbl_areas WHERE id = %s"
        cursor.execute(check_query, (area_id,))
        area = cursor.fetchone()

        if not area:
            print(f"Área con ID {area_id} no encontrada.")
            return {"success": False, "error": "Área no encontrada"}

        # 2. Verificar si existen usuarios asociados en tbl_users
        check_users_query = "SELECT id FROM tbl_users WHERE id_area = %s"
        cursor.execute(check_users_query, (area_id,))
        associated_user = cursor.fetchone()
        if associated_user:
            print(f"No se puede eliminar el área {area_id} porque tiene usuarios asociados.")
            return {"success": False, "error": "Área tiene usuarios asociados"}

        # 3. Proceder a eliminar el área si no tiene usuarios asociados
        delete_query = "DELETE FROM tbl_areas WHERE id = %s"
        cursor.execute(delete_query, (area_id,))
        connection.commit()
        success = cursor.rowcount > 0  # True si se eliminó alguna fila

        return {"success": success}

    except Exception as e:
        connection.rollback()
        print(f"Error al eliminar el área: {e}")
        return {"success": False, "error": str(e)}

    finally:
        cursor.close()
        connection.close()




# Función para obtener los usuarios desde la base de datos
def get_permission():
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener los usuarios
    query = """
        SELECT id, str_name_permission AS namePermission, str_description AS description
        FROM tbl_permissions
    """
    cursor.execute(query)
    permissions = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    connection.close()

    return permissions






















# Función que realiza la consulta
# def get_user(str_name_user: str, str_password: str):
#     connection = create_connection()
#     cursor = connection.cursor(dictionary=True)

#     # Consulta para obtener el usuario y su contraseña
#     query = """
#         SELECT str_name_user, str_email, str_password
#         FROM tbl_users
#         WHERE str_name_user = %s
#     """

#     # Ejecutar la consulta
#     cursor.execute(query, (str_name_user,))
#     user = cursor.fetchone()

#     # Cerrar conexión
#     cursor.close()
#     connection.close()

#     # Verificar si el usuario existe y si la contraseña coincide
#     if user and str_password == user['str_password']:
#         return {"username": user["str_name_user"], "email": user["str_email"]}

#     # Retornar None si la validación falla
#     return None



# Testing the functions
# if __name__ == "__main__":
#     # Test the get_user function (you can change the user details here)
#     user = get_user("some_username", "some_password")
#     if user:
#         print("User found:", user)
#     else:
#         print("User not found or incorrect password.")
    
#     # Test the generate_user_table function
#     table_rows = generate_user_table()
#     print("Generated table rows:")
#     print(table_rows)


# Función principal para interactuar con el usuario
# def main():
#     print("=== Sistema de Autenticación ===")
#     username = input("Ingrese su nombre de usuario: ")
#     password = input("Ingrese su contraseña: ")

#     # Llamar a la función para verificar las credenciales
#     result = get_user(username, password)

#     # Mostrar mensaje de confirmación o error
#     if result:
#         print("OK: Datos de usuario válidos.")
#         print(f"Bienvenido, {result['username']} ({result['email']})")
#     else:
#         print("Error: Credenciales incorrectas.")

# # Ejecutar el programa principal
# if __name__ == "__main__":
#     main()




#PRUEBA DE CONEXION EJECUTABLE
# # Librerías
# import mysql.connector
# from mysql.connector import Error

# Conexión a la base de datos

# def create_connection():
#     connection = None
#     try:
#         # Conectamos con la base de datos
#         connection = mysql.connector.connect(
#             host="127.0.0.1",  # Cambia si tu host es diferente
#             user="root",       # Usuario de la base de datos
#             password="",  # Contraseña del usuario
#             database="db_gdocumental"  # Nombre de la base de datos
#         )
#         if connection.is_connected():
#             print("¡Conexión exitosa a la base de datos!")
#     except Error as e:
#         print(f"Error al conectar: '{e}'")
#     finally:
#         if connection and connection.is_connected():
#             connection.close()
#             print("La conexión ha sido cerrada.")
#         else:
#             print("No se pudo establecer conexión.")
            
# # Ejecutar el script
# if __name__ == "__main__":
#     create_connection()