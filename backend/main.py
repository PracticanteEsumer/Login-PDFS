from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile,Depends,Cookie
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil   
from storage import get_user, get_users,delete_user, add_user
from storage import get_areas,add_area,delete_area
from storage import get_permission
from pydantic import BaseModel

from storage import get_db

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query


app = FastAPI()


# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir cualquier origen (puedes restringirlo)
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Montar la carpeta estática para que FastAPI reconozca los archivos de estilo CSS
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend/static")), name="static")


# Cargar la página de inicio de sesión
@app.get("/", response_class=HTMLResponse)
async def index():
    # Ruta del archivo HTML de inicio
    index_path = os.path.join(os.path.dirname(__file__), "../frontend/inicio.html")
    with open(index_path, "r", encoding="utf-8") as f:
        # Retornamos la respuesta en HTML
        return HTMLResponse(content=f.read(), status_code=200)


# Función para obtener al usuario (incluyendo id, id_permission e id_area)
def get_useR(str_name_user: str, str_password: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT id, str_name_user, str_email, str_password, id_permission, id_area
        FROM tbl_users
        WHERE str_name_user = %s
    """
    cursor.execute(query, (str_name_user,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user and str_password == user['str_password']:
        return {
            "id": user["id"],  # <<-- Asegúrate de incluir este campo
            "username": user["str_name_user"],
            "email": user["str_email"],
            "id_permission": user["id_permission"],
            "id_area": user["id_area"],
        }
    return None

# Función asíncrona para obtener el nombre del área a partir de su id  
# (Se supone que esta consulta se realiza de forma asíncrona, por ejemplo, usando async/await)
async def get_area_by_id(area_id: int, db: Session):
    # Ajusta la consulta según tu base de datos; aquí se usa un ejemplo asíncrono.
    # Si usas una librería que no es asíncrona, puedes hacerlo de forma síncrona.
    query = "SELECT str_name_area FROM tbl_areas WHERE id = %s"
    # Por simplicidad, usamos la sesión de base de datos en modo síncrono
    cursor = db.cursor(dictionary=True)
    cursor.execute(query, (area_id,))
    result = cursor.fetchone()
    cursor.close()
    # En este ejemplo, devolvemos el nombre directamente; si no se encuentra, se devuelve None.
    if result:
        return result["str_name_area"]
    return None



@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    strUsuario: str = Form(...),
    strContrasenna: str = Form(...),
    db_session: Session = Depends(get_db)
):
    # Obtener datos del usuario (asegúrate de usar la función que devuelve el campo "id")
    user = get_user(strUsuario, strContrasenna)
    if user is None:
        raise HTTPException(status_code=401, detail="Nombre de usuario o contraseña incorrectos")

    # Determinar la redirección según el permiso
    id_permission = user["id_permission"]
    if id_permission == 1:
        redirect_url = "/admin"
    elif id_permission == 2:
        redirect_url = "/viewer_downloader"
    elif id_permission == 3:
        redirect_url = "/viewer"
    elif id_permission == 4:
        redirect_url = "/adminArea"
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta vista")

    # Bloque adicional para obtener e imprimir archivos (para depuración)
    user_area_id = user.get("id_area")
    area_name = await get_area_by_id(user_area_id, db_session)  # Usar await si es asíncrona
    if not area_name:
        raise HTTPException(status_code=404, detail="Área no encontrada en la base de datos")
    
    sanitized_area = area_name.strip().replace(" ", "_")
    base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
    folder_path = os.path.join(base_folder, sanitized_area)
    
    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        pdf_files = [file for file in files if file.lower().endswith(".pdf")]
        if pdf_files:
            print(f"Archivos en el área '{area_name}' (carpeta: '{sanitized_area}'): {pdf_files}")
        else:
            print(f"No se encontraron archivos PDF en el área '{area_name}' (carpeta: '{sanitized_area}').")
    else:
        print(f"La carpeta para el área '{area_name}' (carpeta: '{sanitized_area}') no existe.")
    # Fin del bloque adicional

    # Crear la respuesta de redirección y establecer la cookie con el ID del usuario
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(key="user_id", value=str(user["id"]), httponly=True)
    return response


# RUTAS DE USUARIOS 
@app.get("/users", response_class=HTMLResponse)
async def list_users():
    # Obtener los usuarios usando la función de storage.py
    users = get_users()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/usersTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for user in users:
        table_rows += f"""
            <tr>
                <td>{user['username']}</td>
                <td>{user['email']}</td>
                <td>{user['id_permission']}</td>
                <td>{user['id_area']}</td>
                <td>
                    <button class="edit-btn" onclick="editUser({user['id']})">Editar</button>
                    <button class="delete-btn" onclick="deleteUser({user['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/usersJSON")
async def list_users():
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener los usuarios
    query = """
        SELECT id, str_name_user AS username, str_email AS email,str_password AS password, id_permission, id_area
        FROM tbl_users
    """
    cursor.execute(query)
    users = cursor.fetchall()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Retornar los usuarios en formato JSON
    return JSONResponse(content={"users": users})

@app.get("/userById/{user_id}")
async def get_us(user_id: int):
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener un usuario por su ID
    query = """
        SELECT id, str_name_user AS username, str_email AS email,str_password AS password, id_permission, id_area
        FROM tbl_users
        WHERE id = %s
    """
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    if user is None:
        # Si no se encuentra el usuario, devolver un error 404
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Retornar los detalles del usuario en formato JSON
    return JSONResponse(content=user)






@app.get("/users_paginated", response_class=JSONResponse)
async def list_users_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de usuarios con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de usuarios y la paginación
    query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de usuarios por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    users = cursor.fetchall()

    # Consulta para obtener el número total de usuarios
    cursor.execute("SELECT COUNT(*) FROM tbl_users")
    total_users = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_users + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "users": users,
        "total_users": total_users,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }

@app.get("/users_search", response_class=JSONResponse)
async def search_users(query: str = Query(..., alias="query")):
    """
    Busca usuarios por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
        WHERE LOWER(str_name_user) LIKE %s OR LOWER(str_email) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"users": users}

@app.delete("/users/{user_id}")
async def delete_user_route(user_id: int):
    # Llamar a la función de eliminación de usuario
    print(f"Intentando eliminar el usuario con ID: {user_id}")
    success = delete_user(user_id)

    if success:
        # Si el usuario se eliminó con éxito, devolver un mensaje de éxito
        return JSONResponse(status_code=200, content={"message": "Usuario eliminado exitosamente"})
    else:
        # Si no se encontró el usuario o ocurrió algún error, devolver un mensaje de error
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

        
    

# Modelo Pydantic para los datos de entrada del usuario
class UserCreate(BaseModel):
    str_name_user: str
    str_email: str
    str_password: str
    id_permission: int
    id_area: int


# Endpoint para crear el usuario
@app.post("/users/")
async def create_user(user: UserCreate):
    try:
        # Llamar a la función para agregar el usuario a la base de datos
        result = add_user(user.str_name_user, user.str_email, user.str_password, user.id_permission, user.id_area)

        # Verificar el resultado de la función add_user
        if result["success"]:
            return JSONResponse(status_code=201, content={"message": result["message"]})
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        # Si ocurre un error inesperado, devolver un error 500
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")





# Función para obtener usuario por ID antes de actualizar
def get_user_by_id(user_id: int, db):
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT id, str_name_user, str_email, id_permission, id_area FROM tbl_users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")
    
# Modelo Pydantic para la actualización de usuario
class UserUpdate(BaseModel):
    str_name_user: str
    str_email: str
    str_password: str
    id_permission: int
    id_area: int

    class Config:
        extra = "ignore"

async def get_user_update(
    str_name_user: str = Form(...),
    str_email: str = Form(...),
    str_password: str = Form(...),
    id_permission: int = Form(...),
    id_area: int = Form(...)
) -> UserUpdate:
    return UserUpdate(
        str_name_user=str_name_user,
        str_email=str_email,
        str_password=str_password,
        id_permission=id_permission,
        id_area=id_area
    )

# Función para actualizar usuario con validación de área y permiso
def update_user(id: int, name: str, email: str, password: str, id_permission: int, id_area: int, db: Session):
    try:
        # Obtener usuario actual
        user = get_user_by_id(id, db)

        # Validar existencia de área y permiso
        get_permission_and_area(id_permission, id_area, db)

        query = """
            UPDATE tbl_users
            SET str_name_user = %s, str_email = %s, str_password = %s, id_permission = %s, id_area = %s
            WHERE id = %s
        """
        db.execute(query, (name, email, password, id_permission, id_area, id))
        db.commit()
        
        return {"success": True, "message": "Usuario actualizado exitosamente"}
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la actualización: {str(e)}")
    
@app.put("/usersUpdate/{id}")
async def update_user_endpoint(
    id: int,
    user_data: UserUpdate = Depends(get_user_update)
):
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)  # dictionary=True para que los resultados sean dicts si los necesitas

        query = """
            UPDATE tbl_users 
            SET str_name_user = %s, 
                str_email = %s, 
                str_password = %s, 
                id_permission = %s, 
                id_area = %s
            WHERE id = %s
        """
        values = (
            user_data.str_name_user,
            user_data.str_email,
            user_data.str_password,
            user_data.id_permission,
            user_data.id_area,
            id
        )

        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()

        return {"message": "Usuario actualizado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la actualización: {str(e)}")



# Función para obtener información de permisos y áreas
def get_permission_and_area(permission_id: int, area_id: int, db: Session):
    try:
        # Verifica si el permiso existe
        permission_query = "SELECT * FROM tbl_permissions WHERE id = %s"
        permission_result = db.execute(permission_query, (permission_id,))
        permission = permission_result.fetchone()

        # Verifica si el área existe
        area_query = "SELECT * FROM tbl_areas WHERE id = %s"
        area_result = db.execute(area_query, (area_id,))
        area = area_result.fetchone()

        if not permission:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")
        if not area:
            raise HTTPException(status_code=404, detail="Área no encontrada")

        return {"permission": permission, "area": area}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos: {str(e)}")


# RUTAS DE AREAS
@app.get("/areas", response_class=HTMLResponse)
async def list_areas():
    # Obtener los usuarios usando la función de storage.py
    areas = get_areas()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/areaTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for area in areas:
        table_rows += f"""
            <tr>
                <td>{area['nameArea']}</td>
                <td>{area['description']}</td>
                <td>
                    <button class="edit-btn" onclick="editArea({area['id']})">Editar</button>
                    <button class="delete-btn" onclick="deleteArea({area['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/area")
async def get_area():
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener todas las áreas
    query = """
        SELECT id, str_name_area, str_description
        FROM tbl_areas
    """
    cursor.execute(query)
    areas = cursor.fetchall()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    if areas:
        return JSONResponse(content={"areas": areas})
    else:
        return JSONResponse(status_code=404, content={"message": "No se encontraron áreas"})
    

# Modelo Pydantic para los datos de entrada del area
class AreaCreate(BaseModel):
    str_name_area: str
    str_description: str

def sanitize_folder_name(name: str) -> str:
    """
    Sanitiza el nombre del área para que sea seguro utilizarlo como nombre de carpeta.
    Se eliminan espacios al inicio y al final y se reemplazan los espacios intermedios por guiones bajos.
    """
    return name.strip().replace(" ", "_")


# Endpoint para crear el área y la carpeta correspondiente
@app.post("/areas/")
async def create_area(area: AreaCreate):
    try:
        # Llamamos a la función para agregar el área a la base de datos.
        result = add_area(area.str_name_area, area.str_description)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        # Sanitizamos el nombre del área para utilizarlo como nombre de carpeta
        folder_name = sanitize_folder_name(area.str_name_area)

        # Definimos la ruta base donde se almacenarán las carpetas de cada área.
        # Por ejemplo, creamos (o usamos) una carpeta "Areas" en el directorio principal.
        base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
        os.makedirs(base_folder, exist_ok=True)

        # Construimos la ruta completa de la carpeta para el área
        area_folder = os.path.join(base_folder, folder_name)
        os.makedirs(area_folder, exist_ok=True)

        # Retornamos una respuesta exitosa
        return JSONResponse(status_code=201, content={"message": result["message"]})
    
    except Exception as e:
        # En caso de error inesperado, retornamos un error 500.
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/areas_paginated", response_class=JSONResponse)
async def list_areas_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de areas con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de usuarios y la paginación
    query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de areas por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    areas = cursor.fetchall()

    # Consulta para obtener el número total de areas
    cursor.execute("SELECT COUNT(*) FROM tbl_areas")
    total_areas = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_areas + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "areas": areas,
        "total_areas": total_areas,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }

@app.get("/areas_search", response_class=JSONResponse)
async def search_permissions(query: str = Query(..., alias="query")):
    """
    Busca areas por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
        WHERE LOWER(str_name_area) LIKE %s OR LOWER(str_description) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    areas = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"areas": areas}


# @app.delete("/areas/{area_id}")
# async def delete_area_route(area_id: int):
#     print(f"Intentando eliminar el área con ID: {area_id}")
#     result = delete_area(area_id)

#     if result.get("success"):
#         # Eliminación exitosa
#         return JSONResponse(status_code=200, content={"message": "Área eliminada exitosamente"})
#     else:
#         # Dependiendo del error, se puede devolver un código distinto
#         error_message = result.get("error", "Área no encontrada")
#         # Si el error indica que existen usuarios asociados, se devuelve 400
#         if error_message == "Área tiene usuarios asociados":
#             raise HTTPException(status_code=400, detail=error_message)
#         else:
#             raise HTTPException(status_code=404, detail=error_message)

@app.delete("/areas/{area_id}", response_class=JSONResponse)
async def delete_area_route(
    area_id: int,
    user_id: int = Cookie(None),
    db: Session = Depends(get_db)
):
    # Verificar que el usuario esté autenticado mediante la cookie
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado (cookie ausente)")
    
    # (Opcional) Obtener el usuario para validar su existencia
    user = get_user_by_id(int(user_id), db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Intentar eliminar el área de la base de datos
    result = delete_area(area_id)
    if result.get("success"):
        # Si la eliminación fue exitosa, obtener el nombre real del área para construir la ruta a la carpeta
        area_name = await get_area_by_id(area_id, db)
        if not area_name:
            raise HTTPException(status_code=404, detail="Área no encontrada en la base de datos")
        
        # Sanitizar el nombre para formar el nombre de la carpeta
        sanitized_area = area_name.strip().replace(" ", "_")
        base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
        folder_path = os.path.join(base_folder, sanitized_area)
        
        # Eliminar la carpeta si existe
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al eliminar la carpeta: {str(e)}")
        return JSONResponse(status_code=200, content={"message": "Área y carpeta eliminadas exitosamente"})
    else:
        # Si la función delete_area retornó un error, no eliminar la carpeta.
        error_message = result.get("error", "Área no encontrada")
        if error_message == "Área tiene usuarios asociados":
            raise HTTPException(status_code=400, detail=error_message)
        else:
            raise HTTPException(status_code=404, detail=error_message)



# Modelo Pydantic para la actualización de usuario
class AreaUpdate(BaseModel):
    str_name_area: str
    str_description: str

    class Config:
        extra = "ignore"

async def get_area_update(
    str_name_area: str = Form(...),
    str_description: str = Form(...)
) -> AreaUpdate:
    return AreaUpdate(
        str_name_area=str_name_area,
        str_description=str_description
    )

# Función para actualizar usuario con validación de área y permiso
def update_area(id: int, name: str, description: str ,db: Session):
    try:
        # Obtener usuario actual
        area = get_user_by_id(id, db)

        # Validar existencia de área y permiso
        get_permission_and_area(name, description, db)

        query = """
            UPDATE tbl_areas
            SET str_name_area = %s, str_description = %s
            WHERE id = %s
        """
        db.execute(query, (name, description, id))
        db.commit()
        
        return {"success": True, "message": "Area actualizado exitosamente"}
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la actualización: {str(e)}")
    
@app.put("/areasUpdate/{id}")
async def update_area_endpoint(
    id: int,
    area_data: AreaUpdate = Depends(get_area_update),
    db: Session = Depends(get_db)
):
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        # Obtener el nombre actual del área antes de actualizar
        cursor.execute("SELECT str_name_area FROM tbl_areas WHERE id = %s", (id,))
        existing_area = cursor.fetchone()

        if not existing_area:
            raise HTTPException(status_code=404, detail="Área no encontrada")

        old_name = existing_area["str_name_area"]
        new_name = area_data.str_name_area

        # Actualizar en la base de datos
        query = """
            UPDATE tbl_areas
            SET str_name_area = %s, str_description = %s
            WHERE id = %s
        """
        values = (
            new_name,
            area_data.str_description,
            id
        )

        cursor.execute(query, values)
        connection.commit()

        # Renombrar carpeta si el nombre ha cambiado
        if old_name != new_name:
            base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
            old_folder_path = os.path.join(base_folder, old_name.strip().replace(" ", "_"))
            new_folder_path = os.path.join(base_folder, new_name.strip().replace(" ", "_"))

            if os.path.exists(old_folder_path):
                try:
                    os.rename(old_folder_path, new_folder_path)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error al renombrar la carpeta: {str(e)}")

        cursor.close()
        connection.close()

        return {"message": "Área actualizada correctamente."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la actualización: {str(e)}")
    

@app.get("/areaById/{area_id}")
async def get_areaById(area_id: int):
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener un usuario por su ID
    query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
        WHERE id = %s
    """
    cursor.execute(query, (area_id,))
    area = cursor.fetchone()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    if area is None:
        # Si no se encuentra el usuario, devolver un error 404
        raise HTTPException(status_code=404, detail="Area no encontrada")

    # Retornar los detalles del usuario en formato JSON
    return JSONResponse(content=area)


# RUTAS DE PERMISOS 

@app.get("/permissions", response_class=HTMLResponse)
async def list_permissions():
    # Obtener los permisos usando la función de storage.py
    permissions = get_permission()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/permissionTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for permission in permissions:
        table_rows += f"""
            <tr>
                <td>{permission['namePermission']}</td>
                <td>{permission['description']}</td>
                <td>
                    <button class="edit-btn" onclick="editPermission({permission['id']})">Editar</button>
                    <button class="delete-btn" onclick="deletePermission({permission['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)

@app.get("/permission")
async def get_permissions():
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener todos los permisos
    query = """
        SELECT id, str_name_permission
        FROM tbl_permissions
    """
    cursor.execute(query)
    permissions = cursor.fetchall()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    if permissions:
        return JSONResponse(content={"permissions": permissions})
    else:
        return JSONResponse(status_code=404, content={"message": "No se encontraron permisos"})



@app.get("/permissions_paginated", response_class=JSONResponse)
async def list_permissions_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de permisos con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de permisos y la paginación
    query = """
        SELECT id, str_name_permission AS namePermission, str_description AS description
        FROM tbl_permissions
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de permisos por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    permissions = cursor.fetchall()

    # Consulta para obtener el número total de permisos
    cursor.execute("SELECT COUNT(*) FROM tbl_permissions")
    total_permissions = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_permissions + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "permissions": permissions,
        "total_permissions": total_permissions,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }


@app.get("/permissions_search", response_class=JSONResponse)
async def search_permissions(query: str = Query(..., alias="query")):
    """
    Busca permisos por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_permission AS namePermission, str_description AS description
        FROM tbl_permissions
        WHERE LOWER(str_name_permission) LIKE %s OR LOWER(str_description) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    permissions = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"permissions": permissions}








# Vista para permisos de administrador
@app.get("/admin")
async def view_admin():
    # Cargar la página HTML para el administrador
    admin_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewAdmin.html")
    with open(admin_page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    

# Vista para permisos de administrador
@app.get("/adminArea")
async def view_adminForArea():
    # Cargar la página HTML para el administrador
    admin_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewAdminforArea.html")
    with open(admin_page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    
    
@app.get("/api/get-files", response_class=JSONResponse)
async def get_files(user_id: int = Cookie(None), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado (cookie ausente)")
    
    user = get_user_by_id(int(user_id), db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    area_id = user["id_area"]
    area_name = await get_area_by_id(area_id, db)
    if not area_name:
        raise HTTPException(status_code=404, detail="Área no encontrada en la base de datos")
    
    sanitized_area = area_name.strip().replace(" ", "_")
    base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
    folder_path = os.path.join(base_folder, sanitized_area)
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Carpeta del área no encontrada")
    
    files = os.listdir(folder_path)
    pdf_files = [f for f in files if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No se encontraron archivos PDF en el área")
    
    return JSONResponse(content={"files": pdf_files, "folder": sanitized_area})
    
# Vista para permisos de visualización y descarga
@app.get("/viewer_downloader")
async def view_viewer_download():
    #Cargar la página HTML para descargar y ver el pdf
    viewer_download_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewerDownloader.html")
    with open(viewer_download_page_path,"r",encoding="utf-8") as f:
        return HTMLResponse(content=f.read(),status_code=200) 
         

    
# Vista para permisos de visualización
@app.get("/viewer")
async def view_viewer():
    # Cargar la página HTML para el viewer
    viewer_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewer.html")
    with open(viewer_page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

    
# Ruta para eliminar archivos de la carpeta (rol de admin)
@app.delete("/files/{filename}")
async def delete_file(filename: str):
    folder_path = os.path.join(os.path.dirname(__file__), "../CarpetaInfo")
    file_path = os.path.join(folder_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"Archivo '{filename}' eliminado correctamente."}
    else:
        raise HTTPException(status_code=404, detail="No se encontró el archivo a eliminar.")
    

# Ruta para manejar el logout y redirigir al login
@app.post("/logout")
async def logout(response: Response):
    # Eliminar la cookie de sesión
    response.delete_cookie("session") 
    
    # Redirigir al login
    return RedirectResponse(url="/", status_code=303)

# Ruta para subir archivos (rol de admin)
# @app.post("/files/upload")
# async def upload_file(request: Request, file: UploadFile= File(...)):
#     folder_path = os.path.join(os.path.dirname(__file__),"../CarpetaInfo")
#     file_path = os.path.join(folder_path, file.filename)
    
#     with open(file_path,"wb") as f:
#         f.write(await file.read())
#     return{"message": f"Archivo '{file.filename}' subido correctamente a la carpeta."}  

@app.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user_id: int = Cookie(None),
    db: Session = Depends(get_db)
):
    # Verificar que se encuentre el user_id en la cookie
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado (cookie ausente)")

    # Obtener el usuario a partir del user_id
    user = get_user_by_id(int(user_id), db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener el id_area y, a partir de éste, el nombre real del área
    area_id = user["id_area"]
    area_name = await get_area_by_id(area_id, db)
    if not area_name:
        raise HTTPException(status_code=404, detail="Área no encontrada en la base de datos")

    # Sanitizar el nombre del área para formar el nombre de la carpeta (ej. "Recursos Humanos" → "Recursos_Humanos")
    sanitized_area = area_name.strip().replace(" ", "_")

    # Definir la carpeta base donde se almacenan los archivos (por ejemplo, en "../Areas")
    base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
    # Construir la ruta a la carpeta del área
    folder_path = os.path.join(base_folder, sanitized_area)

    # Crear la carpeta si no existe
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al crear la carpeta: {str(e)}")

    # Definir la ruta completa donde se guardará el archivo
    file_path = os.path.join(folder_path, file.filename)

    # Guardar el archivo
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    return JSONResponse(content={"message": f"Archivo '{file.filename}' subido correctamente a la carpeta '{sanitized_area}'."})



@app.api_route("/files/{folder}/{file_name}", methods=["GET", "HEAD", "DELETE"])
async def download_file(folder: str, file_name: str, request: Request):
    # Carpeta general donde se encuentran las áreas
    base_folder = os.path.join(os.path.dirname(__file__), "../Areas")
    folder_path = os.path.join(base_folder, folder)
    file_path = os.path.join(folder_path, file_name)

    if request.method == "DELETE":
        # Lógica para eliminar el archivo
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return JSONResponse(content={"detail": "Archivo eliminado correctamente."})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al eliminar el archivo: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
    else:
        # Lógica para GET y HEAD: retornar el archivo PDF
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="application/pdf", filename=file_name)
        else:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")