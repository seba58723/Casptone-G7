window.PlanillasMgmt = {
    modalPlanillas: null,

    _renderCalibreFila: function(cal, cantidadVal, porcVal) {
        return `
            <div class="col-12 mb-2">
                <div class="d-flex align-items-center bg-dark border border-secondary rounded shadow-sm" style="display: inline-flex !important; width: max-content;">
                    <span class="text-light fw-bold text-uppercase px-3" style="font-size: 0.75rem; letter-spacing: 0.5px; min-width: 130px; text-align: left;">${cal.nombre}</span>
                    <div class="input-group input-group-sm" style="width: 110px;">
                        <span class="input-group-text bg-secondary border-secondary text-light px-2" style="border-radius: 0; font-size: 0.7rem;">CANT</span>
                        <input type="number" min="0" step="1" name="cal_cant_${cal.codigo}" id="cal_cant_${cal.codigo}"
                               class="form-control text-center text-info fw-bold"
                               style="background-color: #0a0d12; border-radius: 0;"
                               value="${cantidadVal}"
                               oninput="window.PlanillasMgmt.recalcularCalibres()">
                    </div>
                    <div class="input-group input-group-sm" style="width: 130px;">
                        <input type="text" name="cal_${cal.codigo}" id="cal_${cal.codigo}"
                               class="form-control text-center text-warning fw-bold border-secondary"
                               style="background-color: #1c2128; border-radius: 0; cursor: not-allowed;"
                               value="${porcVal}" readonly title="Se calcula automaticamente en base a las cantidades">
                        <span class="input-group-text bg-secondary border-secondary text-light px-2" style="border-radius: 0 4px 4px 0; font-size: 0.7rem;">%</span>
                    </div>
                </div>
            </div>
        `;
    },

    recalcularCalibres: function() {
        const inputsCant = document.querySelectorAll('input[id^="cal_cant_"]');
        let total = 0;
        inputsCant.forEach(inp => { total += parseFloat(inp.value) || 0; });

        let sumaPorc = 0;
        inputsCant.forEach(inp => {
            const cant = parseFloat(inp.value) || 0;
            const codigo = inp.id.replace('cal_cant_', '');
            const porcInput = document.getElementById('cal_' + codigo);
            if (porcInput) {
                if (total > 0 && cant > 0) {
                    const porc = (cant / total) * 100;
                    porcInput.value = porc.toFixed(2);
                    sumaPorc += porc;
                } else {
                    porcInput.value = '';
                }
            }
        });

        const totalDiv = document.getElementById('totalCalibresInfo');
        if (totalDiv) {
            if (total > 0) {
                totalDiv.innerHTML = `<i class="fas fa-check-circle text-success me-1"></i> Total de frutos: <strong class="text-warning">${total}</strong> &nbsp;|&nbsp; Suma: <strong class="text-success">${sumaPorc.toFixed(2)}%</strong>`;
                totalDiv.style.display = 'block';
            } else {
                totalDiv.innerHTML = '<i class="fas fa-info-circle text-secondary me-1"></i> <span class="text-secondary">Ingrese cantidad de frutos por calibre para calcular %</span>';
                totalDiv.style.display = 'block';
            }
        }
    },

    init: function() {
        const modalEl = document.getElementById('modalPlanillas');
        if (modalEl) this.modalPlanillas = new bootstrap.Modal(modalEl);
        this.activarBotonEncabezado();
        this.activarBotonColor();
        this.activarBotonCalibre();
        this.activarBotonConsultar();
        this.activarConsultaPorNumero();
        this.activarBotonesLimpiar();
    },

    activarBotonesLimpiar: function() {
        document.querySelectorAll('[data-limpiar]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tipo = e.currentTarget.getAttribute('data-limpiar');
                if (tipo === 'encabezado') {
                    if (confirm('¿Desea limpiar el encabezado para ingresar una PLANILLA NUEVA?')) {
                        document.getElementById('nro_planilla').value = "0";
                        document.getElementById('lote_id_hidden').value = "0";
                        document.getElementById('lote_input').value = "";
                        document.getElementById('guia_despacho').value = "";
                        document.getElementById('bultos_input').value = "";
                        const kgInput = document.getElementById('kilos_input') || document.querySelector('input[name="kg_neto"]');
                        if (kgInput) kgInput.value = "";
                        
                        const candadoHTML = `
                            <div class="col-12 text-center py-4 mt-2 shadow-sm" style="color: #6e7681; border: 1px dashed #3f444a; border-radius: 8px; background-color: rgba(10, 13, 18, 0.5);">
                                <i class="fas fa-lock fa-2x mb-2 text-warning" style="opacity: 0.7;"></i>
                                <h6 class="text-uppercase mb-1" style="letter-spacing: 1px;">Lote Nuevo (En Espera)</h6>
                                <small>Debes presionar <b>Guardar Encabezado</b> para generar las cajas.</small>
                            </div>
                        `;
                        const contenedorCol = document.getElementById('contenedorColor');
                        const contenedorCal = document.getElementById('contenedorCalibre');
                        if (contenedorCol) contenedorCol.innerHTML = candadoHTML;
                        if (contenedorCal) contenedorCal.innerHTML = candadoHTML;

                        // 📸 Encabezado nuevo: no hay planilla todavía, limpiamos la galería de evidencias.
                        if (window.cargarListaEvidencias) window.cargarListaEvidencias();
                    }
                }
            });
        });
    },

    activarConsultaPorNumero: function() {
        const campo = document.getElementById('nro_planilla');
        if (!campo) return;
        campo.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === 'Tab') {
                if (e.key === 'Enter') e.preventDefault(); // con Tab dejamos que el foco avance solo
                const num = parseInt(campo.value, 10);
                const especieId = document.getElementById('especie_id_hidden').value;
                if (!isNaN(num) && num > 0) {
                    this.cargarPlanilla(num, especieId);
                } else if (e.key === 'Enter') {
                    alert("⚠️ Escriba un N° de planilla válido para consultar.");
                }
            }
        });
    },

    obtenerDatosFormulario: function() {
        const form = document.getElementById('formControl');
        const camposBloqueados = form.querySelectorAll(':disabled');
        
        camposBloqueados.forEach(campo => campo.disabled = false);
        const formData = new FormData(form);
        camposBloqueados.forEach(campo => campo.disabled = true);
        
        return formData;
    },

    activarBotonConsultar: function() {
        const btn = document.getElementById('btnConsultarPlanilla');
        if(btn) {
            btn.addEventListener('click', () => {
                const especieId = document.getElementById('especie_id_hidden').value;
                const cliente = document.getElementById('selExp').value;
                const planta = document.getElementById('selPlanta').value;

                if(!cliente || !planta) {
                    alert("⚠️ Seleccione Exportador (Cliente) y Planta primero para ver sus planillas creadas.");
                    return;
                }

                fetch(`/api/planillas-creadas/${especieId}/?cliente=${cliente}&planta=${planta}`)
                .then(r => r.json())
                .then(data => {
                    if(data.estado === 'Exito') {
                        const tbody = document.querySelector('#tablaModalPlanillas tbody');
                        tbody.innerHTML = '';
                        if(data.planillas.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-warning">No hay planillas creadas.</td></tr>';
                        } else {
                            data.planillas.forEach(p => {
                                const tr = document.createElement('tr');
                                tr.style.cursor = 'pointer';
                                tr.innerHTML = `
                                    <td class="text-center fw-bold text-info">${p.planilla}</td>
                                    <td class="text-center">${p.lote}</td>
                                    <td class="text-center">${Utils.formatFecha(p.fecha)}</td>
                                    <td class="text-center text-warning fw-bold">${Utils.formatKg(p.kilos)}</td>
                                    <td class="text-center"><button type="button" class="btn btn-sm btn-outline-success"><i class="fas fa-check"></i></button></td>
                                `;
                                tr.onclick = () => { this.cargarPlanilla(p.planilla, especieId); };
                                tbody.appendChild(tr);
                            });
                        }
                        this.modalPlanillas.show();
                    } else {
                        alert("Error al obtener planillas: " + data.mensaje);
                    }
                });
            });
        }
    },

    cargarPlanilla: function(planillaId, especieId) {
        const contenedorCol = document.getElementById('contenedorColor');
        const contenedorCal = document.getElementById('contenedorCalibre');
        const spinnerHTML = '<div class="col-12 text-center py-3 text-warning"><i class="fas fa-spinner fa-spin fa-2x mb-2"></i><p>Cargando Planilla...</p></div>';

        if(contenedorCol) contenedorCol.innerHTML = spinnerHTML;
        if(contenedorCal) contenedorCal.innerHTML = spinnerHTML;

        fetch(`/api/lote-por-planilla/${especieId}/?planilla=${planillaId}`)
        .then(r => r.json())
        .then(async data => {
            if(data.estado === 'Exito') {
                const d = data.datos;
                document.getElementById('nro_planilla').value = planillaId;

                document.getElementById('selExp').value = d.cliente;
                document.getElementById('selPlanta').value = d.planta;
                document.getElementById('lote_input').value = d.lote;
                // 🚨 ESTO FALTABA: sin el ID interno del lote, al volver a "Guardar
                // Encabezado" se mandaba lote_id_hidden=0 y el guardado pisaba el
                // lote real de esta planilla dejandolo en 0 en la base de datos.
                const inputLoteHidden = document.getElementById('lote_id_hidden');
                if (inputLoteHidden) inputLoteHidden.value = d.lote;
                document.getElementById('guia_despacho').value = d.guia;

                const kgInput = document.getElementById('kilos_input') || document.querySelector('input[name="kg_neto"]');
                const bultosInput = document.getElementById('bultos_input') || document.querySelector('input[name="bultos"]');
                if(kgInput) kgInput.value = Utils.formatCL(d.kg);
                if(bultosInput) bultosInput.value = d.bultos;

                if(d.f_cosecha) document.getElementById('f_cosecha').value = d.f_cosecha;
                if(d.f_recepcion) document.getElementById('f_recepcion').value = d.f_recepcion;

                // La Hora Llegada de ESTA planilla especifica (o vacia si nunca se
                // guardo una), para que no quede pegada la de la planilla anterior.
                const inputHoraCarga = document.getElementById('h_llegada');
                if (inputHoraCarga) inputHoraCarga.value = d.hora_llegada || '';

                const sProd = document.getElementById('selProd');
                const sPred = document.getElementById('selPred');
                const sCuar = document.getElementById('selCuartel');
                const sVar = document.getElementById('selVar');

                sProd.innerHTML = '<option value="">Seleccione...</option>';
                data.listas.productores.forEach(p => sProd.innerHTML += `<option value="${p.id}">${p.nombre}</option>`);
                sProd.value = String(d.productor).split('.')[0];

                sPred.innerHTML = '<option value="">Seleccione...</option>';
                data.listas.predios.forEach(p => sPred.innerHTML += `<option value="${p.id}">${p.nombre}</option>`);
                if(d.predio) sPred.value = String(d.predio).split('.')[0];

                sCuar.innerHTML = '<option value="">Seleccione...</option>';
                data.listas.cuarteles.forEach(c => sCuar.innerHTML += `<option value="${c.id}">${c.nombre}</option>`);
                if(d.cuartel) sCuar.value = String(d.cuartel).split('.')[0];

                let vId = '-1';
                if(d.variedad) {
                    vId = String(d.variedad).split('.')[0];
                    let existe = Array.from(sVar.options).some(opt => opt.value === vId);
                    if(!existe) sVar.add(new Option(`[${vId}] Variedad (Histórica)`, vId));
                    sVar.value = vId;
                }

                fetch(`/api/detalle-planilla/${planillaId}/?especie_id=${especieId}&cliente=${d.cliente}&planta=${d.planta}&variedad=${vId}`)
                .then(r2 => r2.json())
                .then(data2 => {
                    if(data2.estado === 'Exito') {
                        if(contenedorCol && data2.detalles) {
                            contenedorCol.innerHTML = '';
                            data2.detalles.forEach(det => {
                                let valStr = (det.valor !== null && det.valor !== '') ? parseFloat(det.valor).toString() : '';
                                contenedorCol.innerHTML += `
                                    <div class="col-auto mb-3" style="width: 130px;">
                                        <label class="text-uppercase text-truncate" style="font-size: 0.7rem; color: #8b949e; max-width: 100%; display: block;" title="${det.nombre}">${det.nombre}</label>
                                        <div class="input-group input-group-sm shadow-sm">
                                            <input type="number" max="100" min="0" name="col_${det.codigo}" id="col_${det.codigo}" 
                                                   class="form-control text-center text-warning fw-bold px-1" 
                                                   style="background-color: #0a0d12; border-color: #3f444a;" 
                                                   value="${valStr}" oninput="if(this.value > 100) this.value = 100;">
                                            <span class="input-group-text bg-dark border-secondary text-secondary px-2">%</span>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        
                        if(contenedorCal && data2.calibres) {
                            contenedorCal.innerHTML = '';
                            data2.calibres.forEach(cal => {
                                let valStr = (cal.valor !== null && cal.valor !== '') ? parseFloat(cal.valor).toString() : '';
                                let cantStr = (cal.cantidad !== null && cal.cantidad !== undefined && cal.cantidad !== '' && parseFloat(cal.cantidad) > 0) ? parseInt(cal.cantidad).toString() : '';
                                contenedorCal.innerHTML += this._renderCalibreFila(cal, cantStr, valStr);
                            });
                            contenedorCal.innerHTML += `<div id="totalCalibresInfo" class="col-12 mt-3 p-2 border border-secondary rounded" style="background-color: rgba(10, 13, 18, 0.5); font-size: 0.85rem;"></div>`;
                            setTimeout(() => window.PlanillasMgmt.recalcularCalibres(), 50);
                        }

                        // Si esta planilla ya está completa y validada en Sybase, habilitamos
                        // el PDF de una vez, sin obligar a pasar de nuevo por "Guardar Planilla Completa".
                        if (window.PlanillaFinal && typeof window.PlanillaFinal.validarContraSybase === 'function') {
                            const val = window.PlanillaFinal.validarContraSybase(data2);
                            const btnPDF = document.getElementById('btnGenerarPDF');
                            if (btnPDF) btnPDF.disabled = !val.valido;
                        }

                        // 📸 Refrescamos el contador/galería con TODAS las fotos guardadas de esta planilla.
                        if (window.cargarListaEvidencias) window.cargarListaEvidencias();
                    }
                });

                this.modalPlanillas.hide();
                alert(`✅ Planilla N° ${planillaId} cargada con éxito.`);
            } else {
                alert(data.mensaje);
            }
        });
    },

    activarBotonEncabezado: function() {
        const btn = document.getElementById('btnGuardarEncabezado');
        if(!btn) return;
        
        btn.addEventListener('click', async () => {
            const especieId = document.getElementById('especie_id_hidden').value;
            const cliente = document.getElementById('selExp').value;
            const planta = document.getElementById('selPlanta').value;
            const vId = document.getElementById('selVar').value || '-1';

            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
            
            try {
                let formData = this.obtenerDatosFormulario(); 
                const r = await fetch(`/guardar-planilla/${especieId}/`, { method: 'POST', body: formData });
                const data = await r.json();
                
                if(data.estado === 'Error') {
                    alert(data.mensaje); 
                } else if (data.planilla_id) {
                    document.getElementById('nro_planilla').value = data.planilla_id;
                    
                    const contenedorCol = document.getElementById('contenedorColor');
                    const contenedorCal = document.getElementById('contenedorCalibre');
                    
                    if(contenedorCol) contenedorCol.innerHTML = '<div class="col-12 text-center text-warning"><i class="fas fa-spinner fa-spin"></i> Obteniendo colores de Sybase...</div>';
                    if(contenedorCal) contenedorCal.innerHTML = '<div class="col-12 text-center text-warning"><i class="fas fa-spinner fa-spin"></i> Obteniendo calibres de Sybase...</div>';

                    try {
                        const r2 = await fetch(`/api/detalle-planilla/${data.planilla_id}/?especie_id=${especieId}&cliente=${cliente}&planta=${planta}&variedad=${vId}`);
                        const data2 = await r2.json();
                        
                        if(data2.estado === 'Exito') {
                            if(contenedorCol) {
                                contenedorCol.innerHTML = '';
                                if (data2.detalles && data2.detalles.length > 0) {
                                    data2.detalles.forEach(det => {
                                        // Usamos el valor real que ya tenia guardado (si lo tenia), en
                                        // vez de dejar la caja en blanco cada vez que se guarda el
                                        // encabezado — antes esto borraba visualmente los colores de
                                        // una planilla ya cargada aunque en Sybase siguieran intactos.
                                        let strValor = (det.valor !== '' && det.valor !== null) ? parseFloat(det.valor).toString() : '';
                                        contenedorCol.innerHTML += `
                                            <div class="col-auto mb-3" style="width: 130px;">
                                                <label class="text-uppercase text-truncate" style="font-size: 0.7rem; color: #8b949e; max-width: 100%; display: block;" title="${det.nombre}">${det.nombre}</label>
                                                <div class="input-group input-group-sm shadow-sm">
                                                    <input type="number" max="100" min="0" name="col_${det.codigo}" id="col_${det.codigo}" class="form-control text-center text-warning fw-bold px-1" style="background-color: #0a0d12; border-color: #3f444a;" value="${strValor}" oninput="if(this.value > 100) this.value = 100;">
                                                    <span class="input-group-text bg-dark border-secondary text-secondary px-2">%</span>
                                                </div>
                                            </div>
                                        `;
                                    });
                                } else {
                                    contenedorCol.innerHTML = '<p class="text-secondary">No hay colores.</p>';
                                }
                            }

                            if(contenedorCal) {
                                contenedorCal.innerHTML = '';
                                if (data2.calibres && data2.calibres.length > 0) {
                                    data2.calibres.forEach(cal => {
                                        // Mismo caso: mostramos cantidad y % ya guardados, no en blanco.
                                        let valStr = (cal.valor !== null && cal.valor !== '') ? parseFloat(cal.valor).toString() : '';
                                        let cantStr = (cal.cantidad !== null && cal.cantidad !== undefined && cal.cantidad !== '' && parseFloat(cal.cantidad) > 0) ? parseInt(cal.cantidad).toString() : '';
                                        contenedorCal.innerHTML += this._renderCalibreFila(cal, cantStr, valStr);
                                    });
                                    contenedorCal.innerHTML += `<div id="totalCalibresInfo" class="col-12 mt-3 p-2 border border-secondary rounded" style="background-color: rgba(10, 13, 18, 0.5); font-size: 0.85rem;"></div>`;
                                    setTimeout(() => window.PlanillasMgmt.recalcularCalibres(), 50);
                                } else {
                                    contenedorCal.innerHTML = '<p class="text-secondary">No hay calibres.</p>';
                                }
                            }
                        } else {
                            if(contenedorCol) contenedorCol.innerHTML = `<p class="text-danger">❌ Error: ${data2.mensaje}</p>`;
                            if(contenedorCal) contenedorCal.innerHTML = `<p class="text-danger">❌ Error: ${data2.mensaje}</p>`;
                        }
                    } catch (errSP) {
                        if(contenedorCol) contenedorCol.innerHTML = `<p class="text-danger">❌ Falló carga de colores.</p>`;
                        if(contenedorCal) contenedorCal.innerHTML = `<p class="text-danger">❌ Falló carga de calibres.</p>`;
                    }
                    
                    alert(`✅ Encabezado guardado. Planilla N° ${data.planilla_id}`);
                }
            } catch (e) {
                alert("❌ Error crítico al guardar el encabezado.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Encabezado';
            }
        });
    },

    activarBotonColor: function() {
        const btn = document.getElementById('btnGuardarColor');
        if(btn) {
            btn.addEventListener('click', async () => {
                const especieId = document.getElementById('especie_id_hidden').value;
                const planilla = document.getElementById('nro_planilla').value;

                if(!planilla || planilla === '0') { alert("⚠️ Guarda el Encabezado primero."); return; }

                let formData = this.obtenerDatosFormulario(); 
                
                let coloresEnviados = 0;
                let sumaTotalColores = 0;
                document.querySelectorAll('input[id^="col_"], input[name^="col_"]').forEach(inp => {
                    let id = inp.name || inp.id; 
                    let val = inp.value.trim();
                    if(id && id.includes('_') && val !== '') {
                        sumaTotalColores += parseFloat(val);
                        coloresEnviados++;
                        formData.append(id, val);
                    }
                });

                if(coloresEnviados === 0) { alert("⚠️ Las cajas están vacías."); return; }
                if(Math.abs(sumaTotalColores - 100) > 0.1) { alert(`❌ ERROR: Suman ${sumaTotalColores}%. Debe sumar 100%.`); return; }

                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
                try {
                    const r = await fetch(`/guardar-colores/${especieId}/`, { method: 'POST', body: formData });
                    const data = await r.json();
                    alert(data.mensaje);
                } catch (e) { alert("❌ Error al guardar."); } 
                finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Colores';
                }
            });
        }
    },

    activarBotonCalibre: function() {
        const btn = document.getElementById('btnGuardarCalibre');
        if(btn) {
            btn.addEventListener('click', async () => {
                const especieId = document.getElementById('especie_id_hidden').value;
                const planilla = document.getElementById('nro_planilla').value;

                if(!planilla || planilla === '0') { alert("⚠️ Guarda el Encabezado primero."); return; }

                this.recalcularCalibres();

                let formData = this.obtenerDatosFormulario(); 
                
                let calibresEnviados = 0;
                let sumaTotalCalibres = 0;
                let totalCantidad = 0;
                document.querySelectorAll('input[id^="cal_"], input[name^="cal_"]').forEach(inp => {
                    let id = inp.name || inp.id; 
                    let val = inp.value.trim();
                    if (!id) return;
                    if (id.startsWith('cal_cant_')) {
                        if (val !== '') {
                            formData.append(id, val);
                            totalCantidad += parseFloat(val) || 0;
                        }
                        return;
                    }
                    if (id.includes('_') && val !== '') {
                        sumaTotalCalibres += parseFloat(val);
                        calibresEnviados++;
                        formData.append(id, val);
                    }
                });

                if(totalCantidad === 0) { alert("⚠️ Debe ingresar la cantidad de frutos en al menos un calibre."); return; }
                if(calibresEnviados === 0) { alert("⚠️ No hay porcentajes calculados. Ingrese cantidades primero."); return; }
                if(Math.abs(sumaTotalCalibres - 100) > 0.5) { alert(`❌ ERROR: Los porcentajes suman ${sumaTotalCalibres.toFixed(2)}% (debe sumar 100%).\nEsto no deberia pasar; revisa las cantidades ingresadas.`); return; }

                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
                try {
                    const r = await fetch(`/guardar-calibres/${especieId}/`, { method: 'POST', body: formData });
                    const data = await r.json();
                    alert(data.mensaje);
                } catch (e) { alert("❌ Error al guardar."); } 
                finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Calibres';
                }
            });
        }
    }
};