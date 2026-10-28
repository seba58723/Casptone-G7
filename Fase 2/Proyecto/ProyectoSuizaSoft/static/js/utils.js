window.Utils = {
    // Formato chileno: miles con punto y decimales con coma. Ej: 25610 -> "25.610" ; 23447.4 -> "23.447,4" ; 5125.08 -> "5.125,08"
    formatCL: function(num) {
        if (num === null || num === undefined || num === '') return '';
        let strVal = String(num).trim();
        if (strVal === '') return '';
        let n = (typeof num === 'string') ? parseFloat(strVal.replace(/\./g, '').replace(',', '.')) : Number(num);
        if (isNaN(n)) return num;
        
        let parts = n.toString().split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        return parts.join(',');
    },

    // Kilos con la unidad KG. Ej: 25610 -> "25.610 KG" ; 5125.08 -> "5.125,08 KG"
    formatKg: function(num) {
        let res = this.formatCL(num);
        return res ? res + ' KG' : '';
    },

    // Fecha ISO (yyyy-mm-dd) -> chileno dd-mm-yyyy.
    formatFecha: function(fecha) {
        if (!fecha) return '';
        let s = String(fecha).substring(0, 10);
        let p = s.includes('-') ? s.split('-') : (s.includes('/') ? s.split('/') : []);
        if (p.length === 3) {
            if (p[0].length === 4) return `${p[2]}-${p[1]}-${p[0]}`;
        }
        return s;
    }
};