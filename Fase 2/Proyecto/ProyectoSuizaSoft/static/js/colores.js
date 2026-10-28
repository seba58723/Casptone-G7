// static/js/colores.js
// Maneja la sección "Color y Madurez":
// - Renderiza los colores dinámicamente desde Sybase (no hardcodeados)
// - Guarda los valores con Movil_Recep_Actuliza_DetalleColor

(function () {
    'use strict';

    let especieId;
    let coloresActuales = []; // lista de {codigo, nombre, valor} desde Sybase

    function init(opts) {
        especieId = opts.especieId;

        document.getElementById('btnGuardarColores')
            .addEventListener('click', guardarColores);
    }

    /**
     * Renderiza los colores en el acordeón Color y Madurez.
     * Llamado por planillas_mgmt.js después de guardar encabezado,
     * recibiendo la lista de colores que devuelve Movil_Recep_detalleColor.
     *
     * @param {Array} colores - [{codigo, nombre, valor}, ...]
     */
    function renderizarColores(colores) {
        coloresActuales = colores;
        const cont = document.getElementById('contenedorColor');
        cont.innerHTML = '';

        if (!colores || colores.length === 0) {
            cont.innerHTML = '<p class="text-muted small">No hay colores configurados para esta especie.</p>';
            return;
        }

        colores.forEach(c => {
            cont.insertAdjacentHTML('beforeend', `
                <div class="col-md-3 mb-2">
                    <label class="text-white">${c.nombre}</label>
                    <div class="input-group input-group-sm">
                        <input type="number"
                               class="form-control text-center input-color"
                               data-codigo="${c.codigo}"
                               name="color_${c.codigo}"
                               value="${c.valor > 0 ? c.valor : ''}"
                               min="0" max="100" step="0.01"
                               placeholder="0">
                        <span class="input-group-text">%</span>
                    </div>
                </div>
            `);
        });
    }

    /**
     * Guarda los valores de color via API.
     * Requiere que el encabezado ya esté guardado (nro_planilla en el form).
     */
    async function guardarColores() {
        const nroPlanilla = document.getElementById('nro_planilla').value.trim();
        if (!nroPlanilla) {
            notificar('Debes guardar el encabezado primero (Nº de planilla vacío)', 'error');
            return;
        }

        const cliente = document.getElementById('selExp').value;
        const planta = document.getElementById('selPlanta').value;

        // Recoger todos los inputs de color
        const inputs = document.querySelectorAll('.input-color');
        if (inputs.length === 0) {
            notificar('No hay colores para guardar. Guarda el encabezado primero.', 'error');
            return;
        }

        const colores = [];
        inputs.forEach(inp => {
            const valor = inp.value.trim();
            colores.push({
                codigo: parseInt(inp.dataset.codigo),
                valor: valor !== '' ? parseFloat(valor) : 0,
            });
        });

        const btn = document.getElementById('btnGuardarColores');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Guardando...';

        try {
            const resp = await fetch(`/api/guardar-colores/${especieId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    nro_planilla: parseInt(nroPlanilla),
                    cliente: parseInt(cliente),
                    planta: parseInt(planta),
                    colores: colores,
                }),
            });

            const data = await resp.json();

            if (data.estado === 'Exito') {
                notificar(`✓ ${data.mensaje}`, 'success');
            } else if (data.estado === 'Parcial') {
                notificar(`⚠ ${data.mensaje}`, 'info');
                console.warn('Errores parciales:', data.errores);
            } else {
                notificar(`Error: ${data.mensaje}`, 'error');
            }
        } catch (e) {
            notificar(`Error de conexión: ${e.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    }

    // API pública
    window.ColoresCalidad = {
        init,
        renderizarColores,
    };
})();