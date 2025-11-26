from django.contrib import admin
from referencias.models import Caja, Referencia


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['referencia', 'ancho_cm', 'alto_cm', 'profundidad_cm', 'ancho_2d_mm', 'alto_2d_mm']
    list_filter = ['referencia']
    readonly_fields = ['ancho_2d_mm', 'alto_2d_mm']
    fields = [
        'referencia',
        'ancho_cm',
        'alto_cm',
        'profundidad_cm',
        'archivo_cdr',
        'archivo_pdf',
        'ancho_2d_mm',
        'alto_2d_mm',
    ]


@admin.register(Referencia)
class ReferenciaAdmin(admin.ModelAdmin):
    pass