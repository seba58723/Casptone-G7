window.parseNum = function(val) {
    if (val === null || val === undefined || val === '') return 0;
    const numeroStr = String(val).replace(',', '.').trim();
    const numero = parseFloat(numeroStr);
    return isNaN(numero) ? 0 : numero;
};

window.PlanillaCalidad = {
    init: function(configCalidad) {
        this.renderizarTablas(configCalidad);
        this.activarBotonesLimpiar();
        this.iniciarInterceptoresAJAX();
        this.iniciarCalculos();
    },

    renderizarTablas: function(config) {
        const contColor = document.getElementById('contenedorColor');
        if(contColor && config.colores && config.colores.length > 0) {
            contColor.innerHTML = '';
            config.colores.forEach(c => {
                contColor.innerHTML += `
                    <div class="col-md-3 mb-3">
                        <label style="color:#8b949e; font-size:0.75rem; font-weight:bold;">${c.nombre} (ID: ${c.id})</label>
                        <div class="input-group input-group-sm shadow-sm">
                            <input type="number" step="0.1" class="form-control text-center text-warning fw-bold" style="background-color: #0a0d12; border-color: #3f444a;" name="col_${c.id}">
                            <span class="input-group-text" style="background-color: #1c2128; border-color: #3f444a; color: #8b949e;">%</span>
                        </div>
                    </div>`;
            });
        }

        const contParam = document.getElementById('contenedorParametros');
        if(contParam && config.parametros && config.parametros.length > 0) {
            contParam.innerHTML = '';
            config.parametros.forEach(p => {
                contParam.innerHTML += `<div class="col-md-4"><label style="color:var(--accent-fruit) !important">${p}</label><input type="text" class="form-control form-control-sm text-center" name="param_${p.replace(/[^a-zA-Z0-9]/g, '')}"></div>`;
            });
        }

        const contCalibres = document.getElementById('contenedorCalibre');
        if(contCalibres && config.calibres && config.calibres.length > 0) {
            contCalibres.innerHTML = '';
            config.calibres.forEach(c => {
                contCalibres.innerHTML += `
                    <div class="col-md-3 text-center mb-3">
                        <div class="p-2 border border-secondary rounded" style="background-color: rgba(0,0,0,0.2);">
                            <label class="mb-0 text-white">Size ${c.id}</label>
                            <br><small class="text-muted" style="font-size:0.7rem;">(${c.d})</small>
                            <div class="d-flex gap-1 mt-2">
                                <input type="number" class="form-control form-control-sm text-center bg-dark text-white border-secondary" placeholder="Cant." name="cal_cant_${c.id}">
                                <input type="number" step="0.1" class="form-control form-control-sm text-center text-info bg-dark border-secondary" placeholder="%" name="cal_porc_${c.id}">
                            </div>
                        </div>
                    </div>`;
            });
        }
    },

    activarBotonesLimpiar: function() {
        document.querySelectorAll('[data-limpiar]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const seccion = e.currentTarget.dataset.limpiar;
                
                if(seccion === 'encabezado') {
                    document.getElementById('lote_input').value = '';
                    document.getElementById('lote_id_hidden').value = '0';
                    document.getElementById('nro_planilla').value = '0';
                    document.getElementById('guia_despacho').value = '';
                    document.getElementById('bultos_input').value = '';
                    document.getElementById('kilos_input').value = '';
                    document.getElementById('f_cosecha').value = '';
                    const inputHoraLimpiar = document.getElementById('h_llegada');
                    if (inputHoraLimpiar) inputHoraLimpiar.value = '';
                    document.getElementById('selExp').selectedIndex = 0;
                    document.getElementById('selProd').innerHTML = '<option value="">Seleccione...</option>';
                    document.getElementById('selPred').innerHTML = '<option value="">Seleccione...</option>';
                    document.getElementById('selCuartel').innerHTML = '<option value="">Seleccione...</option>';
                    document.getElementById('selVar').selectedIndex = 0;
                    return; 
                }

                let contenedor = null;
                if(seccion === 'color') contenedor = document.getElementById('secColor');
                if(seccion === 'defectos') contenedor = document.getElementById('secDefectos');
                if(seccion === 'calibres') contenedor = document.getElementById('secCalibres');

                if(contenedor) {
                    contenedor.querySelectorAll('input, textarea').forEach(input => {
                        if (input.type !== 'hidden' && input.type !== 'radio') input.value = '';
                        if (input.type === 'radio') input.checked = false;
                    });

                    // Si limpian los defectos, recalcula totales
                    if(seccion === 'defectos') {
                        if (window.sumarTotalesDefectos) window.sumarTotalesDefectos();
                    }
                }
            });
        });
    },

    iniciarInterceptoresAJAX: function() {
        if(window.fetch) {
            const originalFetch = window.fetch;
            window.fetch = async function() {
                const response = await originalFetch.apply(this, arguments);
                const url = arguments[0];
                if (typeof url === 'string' && (url.includes('detalle-planilla') || url.includes('verificar-planilla-lote'))) {
                    response.clone().json().then(data => {
                        window.procesarNuevosModulos(data);
                    }).catch(e => { /* Silencioso */ });
                }
                return response;
            };
        }
        
        let open_original = window.XMLHttpRequest.prototype.open;
        window.XMLHttpRequest.prototype.open = function(method, url) {
            this.addEventListener("load", function() {
                if (typeof url === 'string' && (url.includes('detalle-planilla') || url.includes('verificar-planilla-lote'))) {
                    try {
                        let data = JSON.parse(this.responseText);
                        window.procesarNuevosModulos(data);
                    } catch (e) {}
                }
            });
            open_original.apply(this, arguments);
        };
    },

    iniciarCalculos: function() {
        let inputEst = document.getElementById('est_valor');
        if(inputEst) {
            inputEst.addEventListener('input', function() {
                if (parseFloat(this.value) > 100) this.value = 100;
                if (parseFloat(this.value) < 0) this.value = 0;
            });
        }

        // Permitimos comas y evitamos que destruya el número
        document.addEventListener('input', function(e) {
            if (e.target.classList.contains('calc-porc')) {
                let valor = e.target.value.replace(',', '.');
                valor = valor.replace(/[^0-9.]/g, '');
                
                let partes = valor.split('.');
                if(partes.length > 2) {
                    valor = partes[0] + '.' + partes.slice(1).join('');
                }

                let num = parseFloat(valor);
                if (num > 100) valor = '100';
                
                e.target.value = valor;

                if (window.sumarTotalesDefectos) window.sumarTotalesDefectos();
            }
        });
    }
};

// Suma los totales de defectos por categoría con precisión matemática
window.sumarTotalesDefectos = function() {
    let sum1 = 0, sum2 = 0, sumCom = 0;
    
    document.querySelectorAll('.p1-val').forEach(inp => { sum1 += window.parseNum(inp.value); });
    document.querySelectorAll('.p2-val').forEach(inp => { sum2 += window.parseNum(inp.value); });
    document.querySelectorAll('.pcom-val').forEach(inp => { sumCom += window.parseNum(inp.value); });
    
    // Redondeo matemático
    sum1 = Number(Math.round(sum1 * 100) / 100);
    sum2 = Number(Math.round(sum2 * 100) / 100);
    sumCom = Number(Math.round(sumCom * 100) / 100);

    let t1 = document.getElementById('tot_p1');
    let t2 = document.getElementById('tot_p2');
    let tc = document.getElementById('tot_pcom');
    
    function actualizarColor(el, valor) {
        if (!el) return;
        el.innerText = valor.toFixed(2) + '%';
        el.style.color = (valor >= 100) ? '#ff3333' : '#ffffff';
        el.style.fontWeight = (valor >= 100) ? 'bold' : 'normal';
    }
    
    actualizarColor(t1, sum1);
    actualizarColor(t2, sum2);
    actualizarColor(tc, sumCom);
};

window.procesarNuevosModulos = function(data) {
    let tablaObj = document.getElementById('tablaDefectosObj');
    
    // CABECERA ESTILO EXCEL POE023 - Solo porcentajes
    let thead = `
        <thead class="table-active">
            <tr>
                <th class="text-center border border-secondary" style="width: 40%; background-color: #161b22; color: #cdd9e5;">II. DEFECTOS</th>
                <th class="text-center border border-secondary" style="width: 20%; color: #2ea043; background-color: #161b22;">Fancy (%)</th>
                <th class="text-center border border-secondary" style="width: 20%; color: #f1c40f; background-color: #161b22;">Choice (%)</th>
                <th class="text-center border border-secondary" style="width: 20%; color: #3fb950; background-color: #161b22;">Comercial (%)</th>
            </tr>
        </thead>`;

    if (data.estado === 'Exito' || data.estado === 'Nuevo') {
        if (data.defectos && data.defectos.length > 0) {
            let tbodyHtml = '';
            let currentFactor = null;

            data.defectos.forEach(d => {
                if (d.factor !== currentFactor) {
                    currentFactor = d.factor;
                    let nombreFactor = currentFactor === 1 ? "Calidad" : "Condición";
                    tbodyHtml += `
                        <tr style="background-color: #1c2128;">
                            <td colspan="4" class="text-center fw-bold text-white border border-secondary" style="letter-spacing: 2px; text-transform: uppercase;">${nombreFactor}</td>
                        </tr>`;
                }

                let nombre = d.nombre_defecto ? d.nombre_defecto : 'Defecto #' + d.defecto;

                tbodyHtml += `
                <tr style="background-color: #0d1117;">
                    <td class="text-start align-middle border border-secondary" style="color: #cdd9e5; padding-left: 10px;">
                        <input type="hidden" name="def_factor" value="${d.factor}">
                        <input type="hidden" name="def_codigo" value="${d.defecto}">
                        <input type="hidden" name="def_c1" value="${d.cant1 || 0}">
                        <input type="hidden" name="def_c2" value="${d.cant2 || 0}">
                        <input type="hidden" name="def_ccom" value="${d.cantcom || 0}">
                        <input type="hidden" name="def_total" value="${d.total || 0}">
                        ${nombre}
                    </td>
                    <td class="border border-secondary p-0"><input type="text" class="form-control form-control-sm text-center calc-porc p1-val" name="def_p1" value="${d.porc1 || ''}" style="background:transparent; border:none; color:#2ea043; font-weight:bold;"></td>
                    <td class="border border-secondary p-0"><input type="text" class="form-control form-control-sm text-center calc-porc p2-val" name="def_p2" value="${d.porc2 || ''}" style="background:transparent; border:none; color:#f1c40f; font-weight:bold;"></td>
                    <td class="border border-secondary p-0"><input type="text" class="form-control form-control-sm text-center calc-porc pcom-val" name="def_pcom" value="${d.porccom || ''}" style="background:transparent; border:none; color:#3fb950; font-weight:bold;"></td>
                </tr>`;
            });

            // Fila TOTAL DEFECTOS como en el Excel
            tbodyHtml += `
                <tr style="background-color: #161b22; font-weight: bold; color: white;">
                    <td class="text-center border border-secondary">Total Defectos</td>
                    <td class="text-center border border-secondary" id="tot_p1">0.00%</td>
                    <td class="text-center border border-secondary" id="tot_p2">0.00%</td>
                    <td class="text-center border border-secondary" id="tot_pcom">0.00%</td>
                </tr>`;

            if(tablaObj) tablaObj.innerHTML = thead + `<tbody id="tbody-defectos">${tbodyHtml}</tbody>`;
            if(window.sumarTotalesDefectos) window.sumarTotalesDefectos();

        } else {
            if(tablaObj) tablaObj.innerHTML = thead + '<tbody id="tbody-defectos"><tr><td colspan="4" class="text-center py-4 text-muted">No hay defectos registrados en esta planilla.</td></tr></tbody>';
        }

        if (data.estado === 'Exito') {
            if (data.evaluacion) {
                let eCod = document.getElementById('est_codigo');
                let eVal = document.getElementById('est_valor');
                if(eCod) eCod.value = data.evaluacion.codigo || 1;
                if(eVal) eVal.value = data.evaluacion.valor || '';
            }

            let rbA = document.getElementById('reslot_A');
            let rbR = document.getElementById('reslot_R');
            let obsTexto = document.getElementById('observacion_texto');
            
            if (data.liberacion) {
                if (rbA) rbA.checked = (data.liberacion.estado === 'A');
                if (rbR) rbR.checked = (data.liberacion.estado === 'R');
                if (obsTexto) obsTexto.value = data.liberacion.observacion || '';
            }
        } else if (data.estado === 'Nuevo') {
            let eVal = document.getElementById('est_valor');
            let rbA = document.getElementById('reslot_A');
            let rbR = document.getElementById('reslot_R');
            let obsTexto = document.getElementById('observacion_texto');

            if(eVal) eVal.value = '';
            if(rbA) rbA.checked = false;
            if(rbR) rbR.checked = false;
            if(obsTexto) obsTexto.value = '';
        }
    }
};

window.getDatosBaseComunes = function() {
    let fd = new FormData();
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if(csrfToken) fd.append('csrfmiddlewaretoken', csrfToken.value);
    fd.append('exportador_id', document.getElementById('selExp').value || 0);
    fd.append('planta_id', document.getElementById('selPlanta').value || 0);
    fd.append('nro_planilla', document.getElementById('nro_planilla').value || 0);
    return fd;
};

// GUARDAR DEFECTOS - RESTAURADO A LA VALIDACIÓN CORRECTA (Sin molestar fila por fila)
window.guardarDefectosAjax = function() {
    let fd = window.getDatosBaseComunes();
    if (fd.get('nro_planilla') == 0) return alert('Guarde el encabezado de la planilla primero.');

    let especie_id = document.getElementById('especie_id_hidden').value;
    let filas = document.querySelectorAll('#tbody-defectos tr');
    let procesados = 0;
    let conValores = 0;

    let sum1 = 0, sum2 = 0, sumCom = 0;

    filas.forEach(tr => {
        let factorInput = tr.querySelector('[name="def_factor"]');
        let codigoInput = tr.querySelector('[name="def_codigo"]');
        
        if(factorInput && codigoInput) {
            let p1 = window.parseNum(tr.querySelector('[name="def_p1"]')?.value);
            let p2 = window.parseNum(tr.querySelector('[name="def_p2"]')?.value);
            let pcom = window.parseNum(tr.querySelector('[name="def_pcom"]')?.value);

            sum1 += p1;
            sum2 += p2;
            sumCom += pcom;

            let algunoLleno = (p1 !== 0) || (p2 !== 0) || (pcom !== 0);
            if (algunoLleno) conValores++;

            fd.append('defectos_factor', factorInput.value);
            fd.append('defectos_codigo', codigoInput.value);
            fd.append('defectos_cant1', tr.querySelector('[name="def_c1"]').value);
            fd.append('defectos_porc1', p1);
            fd.append('defectos_cant2', tr.querySelector('[name="def_c2"]').value);
            fd.append('defectos_porc2', p2);
            fd.append('defectos_cantcom', tr.querySelector('[name="def_ccom"]').value);
            fd.append('defectos_porccom', pcom);
            fd.append('defectos_total', tr.querySelector('[name="def_total"]').value);
            procesados++;
        }
    });

    if(procesados === 0) return alert("No hay defectos en la matriz para guardar.");

    // Validación Antigua: Ninguna columna individual debe llegar al 100%
    sum1 = Number(Math.round(sum1 * 100) / 100);
    sum2 = Number(Math.round(sum2 * 100) / 100);
    sumCom = Number(Math.round(sumCom * 100) / 100);

    let malas = [];
    if (sum1 >= 100) malas.push(`Fancy (${sum1}%)`);
    if (sum2 >= 100) malas.push(`Choice (${sum2}%)`);
    if (sumCom >= 100) malas.push(`Comercial (${sumCom}%)`);
    
    if (malas.length > 0) {
        return alert(`⚠️ La(s) columna(s) ${malas.join(', ')} llegan o superan el 100%.\nEso significa que TODA la fruta está defectuosa.\nCorrígelo antes de guardar.`);
    }

    fetch(`/guardar_defectos/${especie_id}/`, { method: 'POST', body: fd })
        .then(res => res.json())
        .then(data => {
            if (data.estado === 'Exito') {
                alert(`✅ Guardado correcto.\n${conValores} defecto(s) con datos, ${procesados - conValores} en 0% (matriz completa sincronizada).`);
            } else {
                alert(data.mensaje);
            }
        })
        .catch(err => alert("Error de conexión al guardar defectos."));
};

window.guardarEstimacionAjax = function() {
    let fd = window.getDatosBaseComunes();
    if (fd.get('nro_planilla') == 0) return alert('Guarde el encabezado de la planilla primero.');

    let especie_id = document.getElementById('especie_id_hidden').value;
    fd.append('cod_evaluacion', document.getElementById('est_codigo').value);
    fd.append('valor_estimacion', document.getElementById('est_valor').value);

    fetch(`/guardar_evaluaciones/${especie_id}/`, { method: 'POST', body: fd })
        .then(res => res.json())
        .then(data => alert(data.mensaje))
        .catch(err => alert("Error de conexión al guardar estimación."));
};

window.guardarLiberacionAjax = function() {
    let fd = window.getDatosBaseComunes();
    if (fd.get('nro_planilla') == 0) return alert('Guarde el encabezado de la planilla primero.');

    let reslot = document.querySelector('input[name="reslot_radio"]:checked');
    if (!reslot) return alert('Debe seleccionar si el lote está Aprobado o Rechazado.');

    let especie_id = document.getElementById('especie_id_hidden').value;
    
    fd.append('ccre_reslot', reslot.value);
    fd.append('ccre_observ', document.getElementById('observacion_texto').value);

    // 📸 La foto de evidencia ya no se manda pegada acá: se sube aparte con el
    // botón "Agregar Foto" (subirFotoEvidencia), al toque de elegirla.

    fetch(`/guardar_liberacion/${especie_id}/`, { method: 'POST', body: fd })
        .then(res => res.json())
        .then(data => alert(data.mensaje))
        .catch(err => alert("Error de conexión al guardar resolución."));
};