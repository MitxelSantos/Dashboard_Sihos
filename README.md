# 🏥 Dashboard SIHOS 2.0

## Hospital Regional Alfonso Jaramillo Salazar
### Sistema de Información Hospitalaria - Dashboard en Tiempo Real

---

## 📋 Descripción

Dashboard moderno y centralizado para visualización de datos hospitalarios con navegación por pestañas, diseño responsive y arquitectura modular.

---

## ✨ Características

- 🎨 **Diseño Moderno**: Glassmorphism, gradientes, animaciones
- 📱 **Responsive**: Optimizado para Desktop, Tablet y Móvil
- 🌓 **Tema Claro/Oscuro**: Switch entre temas
- 🧩 **Modular**: Código centralizado y reutilizable
- ⚡ **Rápido**: Cache inteligente y optimización
- 🎯 **Navegación por Tabs**: Todo en una sola vista
- 🔒 **Seguro**: Conexión read-only a BD

---

## 🚀 Instalación Rápida

### **Prerrequisitos:**
- Python 3.8+
- MySQL/MariaDB
- Streamlit

### **Pasos:**

```bash
# 1. Clonar/Descargar
cd D:\Miguel_Santos\CODE\Dashboard_SIHOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar BD (si es necesario)
# Edita config/settings.py con tus credenciales

# 4. Ejecutar
streamlit run app.py
```

---

## 📁 Estructura del Proyecto

```
Dashboard_SIHOS/
├── app.py                    # Aplicación principal
├── config/
│   └── settings.py          # Configuración central
├── assets/
│   ├── logo.png
│   ├── base.css
│   ├── layout.css
│   └── components.css
├── components/
│   ├── layout.py            # Header, Sidebar, Footer
│   └── widgets.py           # Métricas, Banners
├── pages/
│   ├── admisiones.py
│   ├── facturacion.py
│   ├── medicamentos.py
│   ├── procedimientos.py
│   └── historia_clinica.py
└── utils/
    ├── db_connector.py
    ├── queries.py
    ├── charts.py
    └── helpers.py
```

---

## 🎯 Módulos Disponibles

1. **🏥 Admisiones** - Análisis de admisiones hospitalarias
2. **💰 Facturación** - Control de facturación
3. **💊 Medicamentos** - Prescripciones y medicamentos
4. **🔬 Procedimientos** - Registro de procedimientos
5. **📋 Historia Clínica** - Consulta de historias

---

## ⚙️ Configuración

Toda la configuración está centralizada en `config/settings.py`:

```python
# Personalizar colores
COLORS = {
    "primary": "#2D6A4F",
    "secondary": "#52B788",
    # ...
}

# Configurar BD
DB_CONFIG = {
    "host": "localhost",
    "database": "SIHOS",
    # ...
}

# Otras configuraciones
CACHE_TTL = 300
DEFAULT_THEME = "light"
```

---

## 🎨 Personalización

### **Colores:**
Edita `config/settings.py`:
```python
COLORS = {
    "primary": "#TU_COLOR",
    # ...
}
```

### **Logo:**
Reemplaza `assets/logo.png` con tu logo

### **Estilos:**
Edita archivos CSS en `assets/`:
- `base.css` - Variables y fundamentos
- `layout.css` - Estructura
- `components.css` - Componentes

---

## 📊 Agregar Nueva Página

1. **Crear archivo:**
```python
# pages/mi_nueva_pagina.py

def render_mi_nueva_pagina():
    # Sidebar
    def render_filters():
        st.markdown("## 🔍 Filtros")
        # Tus filtros aquí
    
    with st.sidebar:
        sidebar_wrapper(render_filters)
    
    # Contenido
    render_section_banner("🎯", "Mi Nueva Página")
    # Tu contenido aquí
```

2. **Registrar en settings.py:**
```python
TABS = {
    # ...
    "mi_nueva": {
        "icon": "🎯",
        "title": "Mi Nueva Página",
        "description": "Descripción"
    }
}

TAB_ORDER = [..., "mi_nueva"]
```

3. **Importar en app.py:**
```python
from pages.mi_nueva_pagina import render_mi_nueva_pagina

tab_functions = {
    # ...
    "mi_nueva": render_mi_nueva_pagina,
}
```

---

## 🔧 Mantenimiento

### **Limpiar Cache:**
```bash
streamlit cache clear
```

### **Reiniciar:**
```bash
Ctrl + C
streamlit run app.py
```

### **Actualizar Datos:**
Click en "🔄 Actualizar Datos" en sidebar

---

## 📱 Responsive

El dashboard está optimizado para:

- **Desktop** (1920x1080+): Todas las características
- **Tablet** (1024x768): Ajustes en tamaño
- **Móvil** (375x667+): Layout vertical, tabs apilados

---

## 🐛 Troubleshooting

### **Error: ModuleNotFoundError**
```bash
# Verifica __init__.py
touch config/__init__.py
touch components/__init__.py
touch pages/__init__.py
```

### **Logo no aparece**
```bash
# Verifica ruta
ls assets/logo.png
```

### **CSS no se aplica**
```bash
# Limpia cache
streamlit cache clear
```

### **BD no conecta**
- Verifica credenciales en `config/settings.py`
- Verifica que el servidor MySQL esté corriendo
- Verifica permisos de usuario

---

## 📈 Rendimiento

- **Cache**: 5 minutos (configurable)
- **Queries**: Optimizadas con índices
- **CSS**: Minificado y modular
- **Images**: Optimizadas y en base64

---

## 🔐 Seguridad

- Conexión BD read-only
- Sin credenciales hardcoded
- Sanitización de inputs
- HTTPS recomendado para producción

---

## 📝 Changelog

### v2.0 (2025-12-30)
- ✨ Navegación por tabs
- 🎨 Diseño moderno y responsive
- 🧩 Arquitectura modular
- 🌓 Tema claro/oscuro
- 📊 Componentes reutilizables
- ⚡ Mejoras de rendimiento

### v1.0 (2025-XX-XX)
- 🎉 Versión inicial

---

## 👨‍💻 Desarrollo

### **Agregar dependencia:**
```bash
pip install nueva_libreria
pip freeze > requirements.txt
```

### **Estructura de código:**
- **DRY**: Don't Repeat Yourself
- **Modular**: Un archivo = una responsabilidad
- **Centralizado**: Configuración en un solo lugar
- **Documentado**: Docstrings en funciones

---

## 📚 Documentación Adicional

- [GUIA_MIGRACION.md](GUIA_MIGRACION.md) - Cómo migrar del sistema anterior
- [config/settings.py](config/settings.py) - Configuración detallada
- [components/layout.py](components/layout.py) - Componentes de layout
- [components/widgets.py](components/widgets.py) - Widgets reutilizables

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a branch (`git push origin feature/nueva-funcionalidad`)
5. Abre Pull Request

---

## 📞 Soporte

Para soporte técnico, contacta al equipo de desarrollo del hospital.

---

## 📄 Licencia

© 2025 Hospital Regional Alfonso Jaramillo Salazar. Todos los derechos reservados.

---

**¡Gracias por usar el Dashboard SIHOS 2.0!** 🎉
