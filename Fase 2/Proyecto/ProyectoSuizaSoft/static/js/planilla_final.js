/*
=============================================================================
planilla_final.js - FLUJO DE GUARDADO COMPLETO + HABILITACIÓN PDF
=============================================================================
*/

window.PlanillaFinal = {

    guardarColoreSilent: async function() {
        const especieId = document.getElementById('especie_id_hidden').value;
        const formData = window.PlanillasMgmt.obtenerDatosFormulario();
        
        let suma = 0, llenos = 0;
        document.querySelectorAll('input[id^="col_"], input[name^="col_"]').forEach(inp => {
            let nombre = inp.name || inp.id;
            let val = inp.value.trim();
            if (nombre && val !== '') {
                suma += window.parseNum(val);
                llenos++;
                // Inyectamos el valor a la fuerza de forma limpia
                formData.set(nombre, val); 
            }
        });

        if (llenos === 0) return { estado: 'ErrorValidacion', mensaje: 'Color y Madurez: no hay datos para guardar.' };
        if (Math.abs(suma - 100) > 0.5) return { estado: 'ErrorValidacion', mensaje: `Color y Madurez suma ${suma.toFixed(2)}% (debe sumar 100%).` };

        try {
            const r = await fetch(`/guardar-colores/${especieId}/`, { method: 'POST', body: formData });
            const data = await r.json();
            return data.estado === 'Exito' ? { estado: 'Exito' } : { estado: 'Error', mensaje: 'Color: ' + data.mensaje };
        } catch (e) {
            return { estado: 'Error', mensaje: 'Color: error de conexión.' };
        }
    },

    guardarCalibresSilent: async function() {
        const especieId = document.getElementById('especie_id_hidden').value;
        const formData = window.PlanillasMgmt.obtenerDatosFormulario();
        
        let suma = 0, llenos = 0;
        document.querySelectorAll('input[id^="cal_"], input[name^="cal_"]').forEach(inp => {
            let nombre = inp.name || inp.id;
            let val = inp.value.trim();
            // Solo contar los inputs de PORCENTAJE (cal_X), no de cantidad (cal_cant_X)
            // Los cal_cant_X ya se incluyen en el formData desde obtenerDatosFormulario()
            if (nombre && nombre.startsWith('cal_cant_')) {
                // La cantidad se sube al form pero NO se suma al total del %
                if (val !== '') formData.set(nombre, val);
                return;
            }
            if (nombre && val !== '') {
                suma += window.parseNum(val);
                llenos++;
                // ESTO SALVA AL CALIBRE 123, esté donde esté en el HTML
                formData.set(nombre, val); 
            }
        });

        if (llenos === 0) return { estado: 'ErrorValidacion', mensaje: 'Calibres: no hay datos para guardar.' };
        if (Math.abs(suma - 100) > 0.5) return { estado: 'ErrorValidacion', mensaje: `Calibres suma ${suma.toFixed(2)}% (debe sumar 100%).` };

        try {
            const r = await fetch(`/guardar-calibres/${especieId}/`, { method: 'POST', body: formData });
            const data = await r.json();
            return data.estado === 'Exito' ? { estado: 'Exito' } : { estado: 'Error', mensaje: 'Calibres: ' + data.mensaje };
        } catch (e) {
            return { estado: 'Error', mensaje: 'Calibres: error de conexión.' };
        }
    },
    guardarDefectosSilent: async function() {
        const filas = document.querySelectorAll('#tbody-defectos tr');
        const especieId = document.getElementById('especie_id_hidden').value;
        const formData = window.getDatosBaseComunes();

        let sum1 = 0, sum2 = 0, sumCom = 0;
        let procesados = 0;

        filas.forEach(tr => {
            let factorInput = tr.querySelector('[name="def_factor"]');
            let codigoInput = tr.querySelector('[name="def_codigo"]');

            if (factorInput && codigoInput) {
                let p1 = window.parseNum(tr.querySelector('[name="def_p1"]')?.value);
                let p2 = window.parseNum(tr.querySelector('[name="def_p2"]')?.value);
                let pcom = window.parseNum(tr.querySelector('[name="def_pcom"]')?.value);

                sum1 += p1;
                sum2 += p2;
                sumCom += pcom;

                formData.append('defectos_factor', factorInput.value);
                formData.append('defectos_codigo', codigoInput.value);
                formData.append('defectos_cant1', tr.querySelector('[name="def_c1"]')?.value || 0);
                formData.append('defectos_porc1', p1);
                formData.append('defectos_cant2', tr.querySelector('[name="def_c2"]')?.value || 0);
                formData.append('defectos_porc2', p2);
                formData.append('defectos_cantcom', tr.querySelector('[name="def_ccom"]')?.value || 0);
                formData.append('defectos_porccom', pcom);
                formData.append('defectos_total', tr.querySelector('[name="def_total"]')?.value || 0);
                procesados++;
            }
        });

        if (procesados === 0) return { estado: 'ErrorValidacion', mensaje: 'Defectos: la matriz está vacía.' };

        // Redondeo estricto para evitar decimales trampa
        sum1 = Number(Math.round(sum1 * 100) / 100);
        sum2 = Number(Math.round(sum2 * 100) / 100);
        sumCom = Number(Math.round(sumCom * 100) / 100);

        let malas = [];
        if (sum1 >= 100) malas.push(`Fancy (${sum1}%)`);
        if (sum2 >= 100) malas.push(`Choice (${sum2}%)`);
        if (sumCom >= 100) malas.push(`Comercial (${sumCom}%)`);

        if (malas.length > 0) {
            return {
                estado: 'ErrorValidacion',
                mensaje: `⚠️ DEFECTOS INVÁLIDOS:\nLa(s) columna(s) ${malas.join(', ')} llegan o superan el 100%.\nEso significa que TODA la fruta está defectuosa.\nCorrígelo antes de guardar.`
            };
        }

        try {
            const r = await fetch(`/guardar_defectos/${especieId}/`, { method: 'POST', body: formData });
            const data = await r.json();
            return data.estado === 'Exito'
                ? { estado: 'Exito' }
                : { estado: 'Error', mensaje: 'Defectos: ' + data.mensaje };
        } catch (e) {
            return { estado: 'Error', mensaje: 'Defectos: error de conexión.' };
        }
    },

    guardarEstimacionSilent: async function() {
        const especieId = document.getElementById('especie_id_hidden').value;
        const formData = window.getDatosBaseComunes();
        const valor = document.getElementById('est_valor').value || 0;
        
        // Ahora lee correctamente el código de estimación si existe
        formData.append('cod_evaluacion', document.getElementById('est_codigo')?.value || 1);
        formData.append('valor_estimacion', window.parseNum(valor));

        try {
            const r = await fetch(`/guardar_evaluaciones/${especieId}/`, { method: 'POST', body: formData });
            const data = await r.json();
            return data.estado === 'Exito'
                ? { estado: 'Exito' }
                : { estado: 'Error', mensaje: 'Estimacion: ' + data.mensaje };
        } catch (e) {
            return { estado: 'Error', mensaje: 'Estimacion: error de conexión.' };
        }
    },

    guardarLiberacionSilent: async function() {
        const especieId = document.getElementById('especie_id_hidden').value;
        const estado = document.querySelector('input[name="reslot_radio"]:checked');
        if (!estado) return { estado: 'ErrorValidacion', mensaje: 'Liberación: debes seleccionar Aprobado o Rechazado.' };

        const formData = window.getDatosBaseComunes();
        formData.append('ccre_reslot', estado.value);
        formData.append('ccre_observ', document.getElementById('observacion_texto').value || '');

        // 📸 La foto de evidencia ya no se manda pegada acá: se sube aparte y al
        // toque con el botón "Agregar Foto", sin depender de este guardado.

        try {
            const r = await fetch(`/guardar_liberacion/${especieId}/`, { method: 'POST', body: formData });
            const data = await r.json();
            return data.estado === 'Exito'
                ? { estado: 'Exito' }
                : { estado: 'Error', mensaje: 'Liberacion: ' + data.mensaje };
        } catch (e) {
            return { estado: 'Error', mensaje: 'Liberacion: error de conexión.' };
        }
    },

    validarContraSybase: function(data) {
        const errores = [];

        let sumaColores = 0, hayColores = false;
        (data.detalles || []).forEach(c => {
            if (c.valor !== '') { hayColores = true; sumaColores += window.parseNum(c.valor); }
        });
        if (hayColores && Math.abs(sumaColores - 100) > 0.5)
            errores.push(`Color y Madurez en Sybase suma ${sumaColores.toFixed(2)}% (debe ser 100%).`);

        let sumaCalibres = 0, hayCalibres = false;
        (data.calibres || []).forEach(c => {
            if (c.valor !== '') { hayCalibres = true; sumaCalibres += window.parseNum(c.valor); }
        });
        if (hayCalibres && Math.abs(sumaCalibres - 100) > 0.5)
            errores.push(`Calibres en Sybase suma ${sumaCalibres.toFixed(2)}% (debe ser 100%).`);

        // Validación en Sybase POR COLUMNA
        let t1 = 0, t2 = 0, tc = 0;
        (data.defectos || []).forEach(d => {
            t1 += window.parseNum(d.porc1);
            t2 += window.parseNum(d.porc2);
            tc += window.parseNum(d.porccom);
        });

        t1 = Number(Math.round(t1 * 100) / 100);
        t2 = Number(Math.round(t2 * 100) / 100);
        tc = Number(Math.round(tc * 100) / 100);

        if (t1 >= 100 || t2 >= 100 || tc >= 100) {
            errores.push(`Defectos en Sybase superan el límite. Fancy: ${t1}%, Choice: ${t2}%, Comercial: ${tc}%. Ninguna puede ser 100% o más.`);
        }

        let evaluacionOK = false;
        if (data.evaluacion && data.evaluacion.valor !== '' && window.parseNum(data.evaluacion.valor) !== 0) evaluacionOK = true;

        let liberacionOK = false;
        if (data.liberacion && data.liberacion.estado) liberacionOK = true;

        if (!evaluacionOK) errores.push('Falta guardar la Estimación.');
        if (!liberacionOK) errores.push('Falta guardar la Liberación (Aprobado/Rechazado).');

        return errores.length === 0
            ? { valido: true }
            : { valido: false, errores: errores };
    },

    async guardarTodoYValidar() {
        console.log('🔄 Guardando todas las secciones en cadena...');

        const r1 = await this.guardarColoreSilent();
        if (r1.estado === 'Error') { alert('❌ ' + r1.mensaje); return; }

        const r2 = await this.guardarCalibresSilent();
        if (r2.estado === 'Error') { alert('❌ ' + r2.mensaje); return; }
        if (r2.estado === 'ErrorValidacion') { alert('⚠️ ' + r2.mensaje); return; }

        const r3 = await this.guardarDefectosSilent();
        if (r3.estado === 'Error') { alert('❌ ' + r3.mensaje); return; }
        if (r3.estado === 'ErrorValidacion') { alert('⚠️ ' + r3.mensaje); return; }

        const r4 = await this.guardarEstimacionSilent();
        if (r4.estado === 'Error') { alert('❌ ' + r4.mensaje); return; }

        const r5 = await this.guardarLiberacionSilent();
        if (r5.estado === 'Error') { alert('❌ ' + r5.mensaje); return; }

        console.log('🔍 Verificando contra Sybase...');
        const planillaId = document.getElementById('nro_planilla').value;
        const especieId = document.getElementById('especie_id_hidden').value;
        const cliente = document.querySelector('[name="exportador_id"]').value;
        const planta = document.querySelector('[name="planta_id"]').value;

        try {
            const r = await fetch(`/api/detalle-planilla/${planillaId}/?especie_id=${especieId}&cliente=${cliente}&planta=${planta}`);
            const detalle = await r.json();

            if (detalle.estado !== 'Exito') {
                alert('❌ No se pudo recuperar la planilla de Sybase: ' + detalle.mensaje);
                return;
            }

            const validacion = this.validarContraSybase(detalle);
            if (!validacion.valido) {
                alert('⚠️ VALIDACIÓN CONTRA SYBASE FALLIDA:\n\n' + validacion.errores.join('\n\n'));
                return;
            }

            document.getElementById('btnGenerarPDF').disabled = false;
            alert('✅ PLANILLA COMPLETA GUARDADA EXITOSAMENTE\n\nAhora puedes generar el PDF.');

        } catch (e) {
            alert('❌ Error verificando contra Sybase: ' + e.message);
        }
    }
};

// Conectar el botón
document.addEventListener('DOMContentLoaded', function() {
    const btnSubmit = document.getElementById('btnSubmit');
    if (btnSubmit) {
        btnSubmit.addEventListener('click', () => window.PlanillaFinal.guardarTodoYValidar());
    }

    // Deshabilitar PDF si hay cambios. Usamos delegación de eventos sobre el
    // formulario (en vez de engancharnos a cada input suelto) porque los campos
    // de color, calibre y defectos se crean dinámicamente DESPUÉS de este
    // DOMContentLoaded (al guardar encabezado o cargar un lote/planilla), y con
    // querySelectorAll+forEach esos inputs nuevos quedaban sin el listener.
    const form = document.getElementById('formControl');
    if (form) {
        form.addEventListener('change', (e) => {
            if (e.target.matches('input[id^="col_"], input[id^="cal_"], [name="def_p1"], [name="def_p2"], [name="def_pcom"], #est_valor, input[name="reslot_radio"]')) {
                const btnPDF = document.getElementById('btnGenerarPDF');
                if (btnPDF) btnPDF.disabled = true;
            }
        });
    }

    const btnPDF = document.getElementById('btnGenerarPDF');
    if (btnPDF) {
        btnPDF.addEventListener('click', () => {
            const planillaId = document.getElementById('nro_planilla').value;
            const especieId = document.getElementById('especie_id_hidden').value;
            const cliente = document.querySelector('[name="exportador_id"]').value;
            const planta = document.querySelector('[name="planta_id"]').value;
            const variedad = document.querySelector('[name="variedad_id"]').value;

            const url = `/api/pdf-planilla/${especieId}/?planilla=${planillaId}&cliente=${cliente}&planta=${planta}&variedad=${variedad}`;
            window.open(url, '_blank');
        });
    }
});