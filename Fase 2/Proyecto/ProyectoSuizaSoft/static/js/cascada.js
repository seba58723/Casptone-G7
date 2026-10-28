window.CascadaCalidad = {
    init: function() {
        const sExp = document.getElementById('selExp');
        const sProd = document.getElementById('selProd');
        const sPred = document.getElementById('selPred');
        const sCuar = document.getElementById('selCuartel');

        sExp.addEventListener('change', () => {
            if(!sExp.value) return; 
            fetch(`/api/productores/${sExp.value}/`).then(r => r.json()).then(d => {
                sProd.innerHTML = '<option value="">Seleccione...</option>';
                d.productores.forEach(p => sProd.innerHTML += `<option value="${p.id}">${p.nombre}</option>`);
            });
        });

        sProd.addEventListener('change', () => {
            if(!sProd.value) return;
            fetch(`/api/predios/${sProd.value}/`).then(r => r.json()).then(d => {
                sPred.innerHTML = '<option value="">Seleccione...</option>';
                d.predios.forEach(p => sPred.innerHTML += `<option value="${p.id}">${p.nombre}</option>`);
            });
        });

        sPred.addEventListener('change', () => {
            if(!sProd.value || !sPred.value) return; 
            // Extrae el ID directo del HTML (100% seguro)
            const especieId = document.getElementById('especie_id_hidden').value;
            fetch(`/api/cuarteles/${sProd.value}/${sPred.value}/${especieId}/`).then(r => r.json()).then(d => {
                sCuar.innerHTML = '<option value="">Seleccione...</option>';
                d.cuarteles.forEach(c => sCuar.innerHTML += `<option value="${c.id}" data-vid="${c.v_id}">${c.nombre}</option>`);
            });
        });
    }
};