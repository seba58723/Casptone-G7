window.LotesCalidad = {
    modal: null,

    init: function() {
        this.modal = new bootstrap.Modal(document.getElementById('modalLotes'));
        this.activarBuscadores();
    },

    activarBuscadores: function() {
        const sExp = document.getElementById('selExp');
        const sPlanta = document.getElementById('selPlanta');

        document.getElementById('btnBuscarLoteExacto').addEventListener('click', () => {
            this.buscarLoteExacto();
        });

        // Permite buscar el lote presionando Enter o Tab dentro del campo, sin
        // necesidad de hacer clic en la lupa.
        document.getElementById('lote_input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === 'Tab') {
                if (e.key === 'Enter') e.preventDefault(); // con Tab dejamos que el foco avance solo
                const lote = document.getElementById('lote_input').value.trim();
                if (lote !== '') this.buscarLoteExacto();
            }
        });

        document.getElementById('btnVerLotes').addEventListener('click', () => {
            if(!sExp.value) { alert("Seleccione Exportador primero."); return; }
            const sProd = document.getElementById('selProd');
            if(!sProd || !sProd.value) { alert("Seleccione un Productor primero para ver solo sus lotes pendientes."); return; }
            const especieId = document.getElementById('especie_id_hidden').value;
            const prodId = String(sProd.value).split('.')[0];

            fetch(`/api/buscar-lote/${especieId}/?planta=${sPlanta.value}&cliente=${sExp.value}&productor=${prodId}`)
            .then(r=>r.json()).then(d => {
                const tbody = document.querySelector('#tablaModalLotes tbody'); 
                tbody.innerHTML = '';
                if(!d.lotes || d.lotes.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-warning">No hay lotes pendientes para este productor.</td></tr>';
                } else {
                    d.lotes.forEach(l => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td class="text-left-aligned fw-bold text-info">${l.lote}</td>
                            <td class="text-left-aligned">${l.variedad_nombre}</td>
                            <td class="text-right-aligned">${l.guia}</td>
                            <td class="text-right-aligned">${Utils.formatFecha(l.fecha_recepcion)}</td>
                            <td class="text-right-aligned">${l.bultos}</td>
                            <td class="text-right-aligned fw-bold text-warning">${Utils.formatKg(l.kg_neto)}</td>
                            <td class="text-center"><button type="button" class="btn-check-custom"><i class="fas fa-check"></i></button></td>`;
                        tr.onclick = () => { 
                            this.autoLlenarFormulario(l, especieId); 
                            this.modal.hide(); 
                        };
                        tbody.appendChild(tr);
                    });
                }
                this.modal.show();
            });
        });
    },

    buscarLoteExacto: function() {
        const sExp = document.getElementById('selExp');
        const sPlanta = document.getElementById('selPlanta');
        const lote = document.getElementById('lote_input').value;
        const especieId = document.getElementById('especie_id_hidden').value;

        fetch(`/api/buscar-lote/${especieId}/?lote=${lote}&planta=${sPlanta.value}&cliente=${sExp.value}`)
        .then(r=>r.json()).then(d => {
            if(d.estado === 'Exito') this.autoLlenarFormulario(d.datos, especieId);
            else alert("Lote no encontrado");
        });
    },

    autoLlenarFormulario: async function(l, especieId) {
        const contenedorCol = document.getElementById('contenedorColor');
        const contenedorCal = document.getElementById('contenedorCalibre');
        const spinnerHTML = '<div class="col-12 text-center py-3 text-warning"><i class="fas fa-spinner fa-spin fa-2x mb-2"></i><p>Cargando datos del lote...</p></div>';

        if(contenedorCol) contenedorCol.innerHTML = spinnerHTML;
        if(contenedorCal) contenedorCal.innerHTML = spinnerHTML;

        // 🚨 BLINDAJE CONTRA SOBRESCRITURA 🚨
        // Apenas el usuario selecciona un lote, forzamos que el Nº Planilla sea 0 de INMEDIATO.
        // Así evitamos que se quede pegado el número de una planilla que estabas viendo antes.
        const inputPlanilla = document.getElementById('nro_planilla');
        if (inputPlanilla) {
            inputPlanilla.value = "0";
        }
        // Misma logica: la Hora Llegada tampoco debe quedar pegada del lote
        // anterior. Si esta planilla ya tenia una guardada, se repone mas
        // abajo con la respuesta de /api/verificar-planilla-lote/.
        const inputHora = document.getElementById('h_llegada');
        if (inputHora) {
            inputHora.value = '';
        }

        document.getElementById('lote_input').value = l.lote;
        document.getElementById('lote_id_hidden').value = l.lote_id; 
        document.getElementById('guia_despacho').value = l.guia;
        
        const kgInput = document.getElementById('kilos_input') || document.querySelector('input[name="kg_neto"]');
        const bultosInput = document.getElementById('bultos_input') || document.querySelector('input[name="bultos"]');
        if(kgInput) kgInput.value = Utils.formatCL(l.kg_neto);
        if(bultosInput) bultosInput.value = l.bultos;
        
        if(l.fecha_cosecha) document.getElementById('f_cosecha').value = l.fecha_cosecha;
        if(l.fecha_recepcion) document.getElementById('f_recepcion').value = l.fecha_recepcion;

        const sProd = document.getElementById('selProd');
        const sPred = document.getElementById('selPred');
        const sCuar = document.getElementById('selCuartel');

        if(l.productor_id) {
            let pId = String(l.productor_id).split('.')[0];
            sProd.value = pId;
            const resPred = await fetch(`/api/predios/${pId}/`);
            const dPred = await resPred.json();
            sPred.innerHTML = '<option value="">Seleccione...</option>';
            dPred.predios.forEach(p => sPred.innerHTML += `<option value="${p.id}">${p.nombre}</option>`);
            
            if(l.predio_id) {
                let preId = String(l.predio_id).split('.')[0];
                sPred.value = preId;
                const resCuar = await fetch(`/api/cuarteles/${pId}/${preId}/${especieId}/`);
                const dCuar = await resCuar.json();
                sCuar.innerHTML = '<option value="">Seleccione...</option>';
                dCuar.cuarteles.forEach(c => sCuar.innerHTML += `<option value="${c.id}" data-vid="${c.v_id}">${c.nombre}</option>`);
                if(l.cuartel_id) sCuar.value = String(l.cuartel_id).split('.')[0];
            }
        }

        let vId = '-1';
        if(l.variedad_id) {
            const sVar = document.getElementById('selVar');
            vId = String(l.variedad_id).split('.')[0];
            let vNombre = l.variedad_nombre ? l.variedad_nombre : "Variedad (Histórica)";
            let existe = Array.from(sVar.options).some(opt => opt.value === vId);
            if(!existe) sVar.add(new Option(`[${vId}] ${vNombre}`, vId));
            sVar.value = vId;
        }

        const cliente = document.getElementById('selExp').value;
        const planta = document.getElementById('selPlanta').value;
        
        fetch(`/api/verificar-planilla-lote/${especieId}/?cliente=${cliente}&planta=${planta}&lote_id=${l.lote_id}&variedad=${vId}`)
        .then(r => r.json())
        .then(res => {
            if(res.estado === 'Exito') {
                // Solo si la base de datos confirma que ESTE lote YA TIENE planilla, ponemos su número.
                document.getElementById('nro_planilla').value = res.planilla_id;

                // Repone la Hora Llegada que se guardó con esta planilla (si el backend la encontró).
                if (res.hora_llegada) {
                    const inputHoraRes = document.getElementById('h_llegada');
                    if (inputHoraRes) inputHoraRes.value = res.hora_llegada;
                }

                fetch(`/api/detalle-planilla/${res.planilla_id}/?especie_id=${especieId}&cliente=${cliente}&planta=${planta}&variedad=${vId}`)
                .then(r2 => r2.json())
                .then(data2 => {
                    if(data2.estado === 'Exito') {
                        if(contenedorCol && data2.detalles) {
                            contenedorCol.innerHTML = '';
                            data2.detalles.forEach(det => {
                                let strValor = (det.valor !== '' && det.valor !== null) ? parseFloat(det.valor).toString() : '';
                                contenedorCol.innerHTML += `
                                    <div class="col-auto mb-3" style="width: 130px;">
                                        <label class="text-uppercase text-truncate" style="font-size: 0.7rem; color: #8b949e; max-width: 100%; display: block;" title="${det.nombre}">${det.nombre}</label>
                                        <div class="input-group input-group-sm shadow-sm">
                                            <input type="number" max="100" min="0" name="col_${det.codigo}" id="col_${det.codigo}" 
                                                   class="form-control text-center text-warning fw-bold px-1" 
                                                   style="background-color: #0a0d12; border-color: #3f444a;" 
                                                   value="${strValor}" 
                                                   oninput="if(this.value > 100) this.value = 100;">
                                            <span class="input-group-text bg-dark border-secondary text-secondary px-2">%</span>
                                        </div>
                                    </div>`;
                            });
                        }
                        
                        if(contenedorCal && data2.calibres) {
                            contenedorCal.innerHTML = '';
                            data2.calibres.forEach(cal => {
                                let valStr = (cal.valor !== null && cal.valor !== '') ? parseFloat(cal.valor).toString() : '';
                                let cantStr = (cal.cantidad !== null && cal.cantidad !== undefined && cal.cantidad !== '' && parseFloat(cal.cantidad) > 0) ? parseInt(cal.cantidad).toString() : '';
                                contenedorCal.innerHTML += window.PlanillasMgmt._renderCalibreFila(cal, cantStr, valStr);
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

                        // 📸 Refrescamos el contador/galería con TODAS las fotos guardadas de este lote.
                        if (window.cargarListaEvidencias) window.cargarListaEvidencias();
                    }
                });
            } else {
                // Si el lote es Nuevo, aseguramos que quede en 0 y bloqueamos.
                document.getElementById('nro_planilla').value = "0";

                // 📸 Lote nuevo: no hay planilla ni fotos todavía, limpiamos la galería.
                if (window.cargarListaEvidencias) window.cargarListaEvidencias();

                const candadoHTML = `
                    <div class="col-12 text-center py-4 mt-2 shadow-sm" style="color: #6e7681; border: 1px dashed #3f444a; border-radius: 8px; background-color: rgba(10, 13, 18, 0.5);">
                        <i class="fas fa-lock fa-2x mb-2 text-warning" style="opacity: 0.7;"></i>
                        <h6 class="text-uppercase mb-1" style="letter-spacing: 1px;">Lote Nuevo (En Espera)</h6>
                        <small>Debes presionar <b>Guardar Encabezado</b> para generar las cajas.</small>
                    </div>
                `;
                if(contenedorCol) contenedorCol.innerHTML = candadoHTML;
                if(contenedorCal) contenedorCal.innerHTML = candadoHTML;
            }
        });
    }
};