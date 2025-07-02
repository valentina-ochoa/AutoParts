// dashboard.js - Lógica JS para el dashboard de administración
// Inicializa popovers y tooltips de Bootstrap 3 tras cada carga dinámica
$(function(){
    console.log('[DASHBOARD] DOM ready');
    $('#dashboardTabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Abrir modal y cargar datos del producto
    $('.btn-editar-producto').on('click', function() {
        var btn = $(this);
        $('#editProductoId').val(btn.data('id'));
        $('#editNombre').val(btn.data('nombre'));
        $('#editProveedor').val(btn.data('proveedor'));
        $('#editPrecio').val(btn.data('precio'));
        $('#editStock').val(btn.data('stock'));
        $('#editEstado').val(btn.data('estado'));
        // Mostrar imagen actual en el modal de edición
        var imgUrl = btn.data('imagen');
        if(imgUrl) {
            $('#editImagenPreview').attr('src', imgUrl);
        } else {
            $('#editImagenPreview').attr('src', '/static/imgProductos/placeholder.png');
        }
        $('#editImagen').val(""); // Limpiar input file
        $('#modalEditarProducto').modal('show');
    });

    $('.btn.btn-success.pull-right').on('click', function(e) {
        e.preventDefault();
        $('#formNuevoProducto')[0].reset();
        $('#modalNuevoProducto').modal('show');
    });
    $('.btn.btn-success.pull-right').removeAttr('data-toggle').removeAttr('data-target');

    // Edición de producto con imagen
    $('#formEditarProducto').on('submit', function(e){
        e.preventDefault();
        var form = $(this)[0];
        var formData = new FormData(form);
        var btn = $(this).find('button[type="submit"]');
        var errorDiv = $('#editarProductoError');
        errorDiv.hide().text("");
        btn.prop('disabled', true);
        $.ajax({
            url: '/api/producto/editar/',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(resp) {
                if(resp.status === 'ok') {
                    $('#modalEditarProducto').modal('hide');
                    var id = $('#editProductoId').val();
                    var row = $('input[name="seleccionados"][value="'+id+'"]').closest('tr');
                    row.find('td:eq(1)').text($('#editNombre').val());
                    row.find('td:eq(2)').text($('#editProveedor').val()); // Corregido: proveedor va en la columna 2
                    row.find('input[name="precio_'+id+'"]').val($('#editPrecio').val());
                    row.find('input[name="stock_'+id+'"]').val($('#editStock').val());
                    row.find('select[name="estado_'+id+'"]').val($('#editEstado').val());
                    // Actualizar atributos data-* del botón Editar para reflejar los nuevos datos
                    var btnEditar = row.find('.btn-editar-producto');
                    btnEditar.data('nombre', $('#editNombre').val());
                    btnEditar.data('proveedor', $('#editProveedor').val());
                    btnEditar.data('precio', $('#editPrecio').val());
                    btnEditar.data('stock', $('#editStock').val());
                    btnEditar.data('estado', $('#editEstado').val());
                    if(resp.imagen_url) {
                        btnEditar.data('imagen', resp.imagen_url);
                    }
                    $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                        '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                        '¡Producto actualizado con éxito!'+
                    '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                } else {
                    errorDiv.text(resp.msg || 'Error desconocido').show();
                }
                btn.prop('disabled', false);
            },
            error: function() {
                errorDiv.text('Error de red al guardar los cambios.').show();
                btn.prop('disabled', false);
            }
        });
    });

    $('#formNuevoProducto').on('submit', function(e) {
        e.preventDefault();
        var form = $(this)[0];
        var formData = new FormData(form);
        // Agregar descripción manualmente si no la toma el FormData (por seguridad)
        formData.set('descripcion', $('#nuevoDescripcion').val());
        var btn = $(this).find('button[type="submit"]');
        var errorDiv = $('#nuevoProductoError');
        errorDiv.hide().text("");
        var precio = parseFloat($('#nuevoPrecio').val());
        if (isNaN(precio) || precio <= 0) {
            errorDiv.text('El precio debe ser mayor a 0.').show();
            btn.prop('disabled', false);
            return;
        }
        btn.prop('disabled', true);
        $.ajax({
            url: '/api/producto/crear/',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(resp) {
                if(resp.status === 'ok') {
                    $('#modalNuevoProducto').modal('hide');
                    $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                        '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                        '¡Producto creado con éxito!'+
                    '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                    setTimeout(function(){ location.reload(); }, 1200);
                } else {
                    errorDiv.text(resp.msg || 'Error desconocido').show();
                }
                btn.prop('disabled', false);
            },
            error: function() {
                errorDiv.text('Error de red al crear el producto.').show();
                btn.prop('disabled', false);
            }
        });
    });

    $('#dashboardTabs a').on('shown.bs.tab', function (e) {
        localStorage.setItem('dashboardTab', $(e.target).attr('href'));
    });
    var lastTab = localStorage.getItem('dashboardTab');
    if(lastTab) {
        $('#dashboardTabs a[href="'+lastTab+'"], #dashboardTabs a[data-target="'+lastTab+'"], #dashboardTabs a').filter(function(){return $(this).attr('href')===lastTab;}).tab('show');
    }

    $('#checkAllProductos').on('change', function() {
        var checked = $(this).prop('checked');
        $('input[name="seleccionados"]').prop('checked', checked);
    });

    // --- POPUPS DE ACCIONES MASIVAS Y ELIMINACIÓN ---
    // Modal de confirmación para eliminar (individual o masivo)
    var idsAEliminarMasivo = [];
    $('.btn-eliminar-masivo').off('click').on('click', function() {
        var seleccionados = [];
        $('input[name="seleccionados"]:checked').each(function(){
            seleccionados.push($(this).val());
        });
        if(seleccionados.length === 0) {
            alert('Selecciona al menos un producto.');
            return;
        }
        idsAEliminarMasivo = seleccionados;
        $('#nombreProductoEliminar').html('los <b>' + seleccionados.length + '</b> productos seleccionados');
        $('#modalConfirmarEliminar .modal-header').css('background', '#d9534f');
        $('#modalConfirmarEliminar .modal-content').css('border', '2px solid #d9534f');
        $('#modalConfirmarEliminar .modal-title').html('<i class="fa fa-exclamation-triangle"></i> Confirmar eliminación');
        $('#modalConfirmarEliminar .modal-body').html('¿Está seguro que desea eliminar los <b>' + seleccionados.length + '</b> productos seleccionados?<br><span style="font-size:13px; color:#a94442;">Esta acción no se puede deshacer.</span>');
        $('#btnConfirmarEliminarProducto').removeClass().addClass('btn btn-danger').text('Eliminar');
        $('#modalConfirmarEliminar').data('masivo', true).data('accion-masiva', false).modal('show');
    });

    // Modal de confirmación para activar/desactivar/descontinuar
    var accionMasivaPendiente = null;
    var idsAccionMasiva = [];
    $('.btn-accion-masiva').off('click').on('click', function() {
        var accion = $(this).data('accion');
        var seleccionados = [];
        $('input[name="seleccionados"]:checked').each(function(){
            seleccionados.push($(this).val());
        });
        if(seleccionados.length === 0) {
            alert('Selecciona al menos un producto.');
            return;
        }
        accionMasivaPendiente = accion;
        idsAccionMasiva = seleccionados;
        var config = {
            'activo': {
                color: '#337ab7', border: '#2e6da4', icon: 'fa-check-circle', title: 'Confirmar activación', btn: 'btn-primary', btnText: 'Activar', msg: '¿Está seguro que desea <b>activar</b> los <b>' + seleccionados.length + '</b> productos seleccionados?'
            },
            'inactivo': {
                color: '#f0ad4e', border: '#eea236', icon: 'fa-ban', title: 'Confirmar desactivación', btn: 'btn-warning', btnText: 'Desactivar', msg: '¿Está seguro que desea <b>desactivar</b> los <b>' + seleccionados.length + '</b> productos seleccionados?'
            },
            'descontinuado': {
                color: '#5bc0de', border: '#46b8da', icon: 'fa-archive', title: 'Confirmar descontinuación', btn: 'btn-info', btnText: 'Descontinuar', msg: '¿Está seguro que desea <b>descontinuar</b> los <b>' + seleccionados.length + '</b> productos seleccionados?'
            }
        };
        var c = config[accion];
        $('#nombreProductoEliminar').html('los <b>' + seleccionados.length + '</b> productos seleccionados');
        $('#modalConfirmarEliminar .modal-header').css('background', c.color);
        $('#modalConfirmarEliminar .modal-content').css('border', '2px solid ' + c.border);
        $('#modalConfirmarEliminar .modal-title').html('<i class="fa ' + c.icon + '"></i> ' + c.title);
        $('#modalConfirmarEliminar .modal-body').html(c.msg);
        $('#btnConfirmarEliminarProducto').removeClass().addClass('btn ' + c.btn).text(c.btnText);
        $('#modalConfirmarEliminar').data('masivo', false).data('accion-masiva', true).modal('show');
    });

    // Handler único para el botón de confirmación del modal
    $('#btnConfirmarEliminarProducto').off('click').on('click', function() {
        var btn = $(this);
        btn.prop('disabled', true);
        var esEliminarMasivo = $('#modalConfirmarEliminar').data('masivo');
        var esAccionMasiva = $('#modalConfirmarEliminar').data('accion-masiva');
        if(esEliminarMasivo) {
            // Borrado masivo
            $.ajax({
                url: '/api/producto/eliminar_masivo/',
                method: 'POST',
                data: {
                    'ids': idsAEliminarMasivo.join(','),
                    'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
                },
                success: function(resp) {
                    if(resp.status === 'ok') {
                        $('#modalConfirmarEliminar').modal('hide');
                        $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                            '¡Productos eliminados con éxito!'+
                        '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                        setTimeout(function(){ location.reload(); }, 1200);
                    } else {
                        alert('Error: ' + (resp.msg || 'Error desconocido'));
                    }
                    btn.prop('disabled', false);
                },
                error: function() {
                    alert('Error de red al eliminar los productos.');
                    btn.prop('disabled', false);
                }
            });
            $('#modalConfirmarEliminar').data('masivo', false);
        } else if(esAccionMasiva) {
            // Acción masiva (activar, desactivar, descontinuar)
            $.ajax({
                url: '/api/producto/accion_masiva/',
                method: 'POST',
                data: {
                    'ids': idsAccionMasiva.join(','),
                    'accion': accionMasivaPendiente,
                    'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
                },
                success: function(resp) {
                    if(resp.status === 'ok') {
                        $('#modalConfirmarEliminar').modal('hide');
                        $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                            '¡Acción masiva realizada con éxito!'+
                        '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                        setTimeout(function(){ location.reload(); }, 1200);
                    } else {
                        alert('Error: ' + (resp.msg || 'Error desconocido'));
                    }
                    btn.prop('disabled', false);
                },
                error: function() {
                    alert('Error de red al realizar la acción.');
                    btn.prop('disabled', false);
                }
            });
            $('#modalConfirmarEliminar').data('accion-masiva', false);
        } else {
            // Borrado individual
            var id = productoAEliminar;
            var row = rowAEliminar;
            $.ajax({
                url: '/api/producto/eliminar/',
                method: 'POST',
                data: {
                    'id': id,
                    'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
                },
                success: function(resp) {
                    if(resp.status === 'ok') {
                        $('#modalConfirmarEliminar').modal('hide');
                        row.fadeOut(400, function(){ $(this).remove(); });
                        $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                            '¡Producto eliminado con éxito!'+
                        '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                    } else {
                        alert('Error al eliminar: ' + (resp.msg || 'Error desconocido'));
                    }
                    btn.prop('disabled', false);
                },
                error: function() {
                    alert('Error de red al eliminar el producto.');
                    btn.prop('disabled', false);
                }
            });
        }
    });
    // Al cerrar el modal, limpiar flags y restaurar texto
    $('#modalConfirmarEliminar').on('hidden.bs.modal', function(){
        $(this).data('masivo', false);
        $(this).data('accion-masiva', false);
        $('#nombreProductoEliminar').text('');
        $('#btnConfirmarEliminarProducto').removeClass().addClass('btn btn-danger').text('Eliminar');
        $('#modalConfirmarEliminar .modal-header').css('background', '#d9534f');
        $('#modalConfirmarEliminar .modal-content').css('border', '2px solid #d9534f');
        $('#modalConfirmarEliminar .modal-title').html('<i class="fa fa-exclamation-triangle"></i> Confirmar eliminación');
        $('#modalConfirmarEliminar .modal-body').html('¿Está seguro que desea eliminar el producto <b id="nombreProductoEliminar"></b>?<br><span style="font-size:13px; color:#a94442;">Esta acción no se puede deshacer.</span>');
    });

    // Filtros: solo se aplica al presionar el botón Filtrar
    // $('#formFiltroProductos input, #formFiltroProductos select').on('change', function() {
    //     $('#formFiltroProductos').submit();
    // });
    // --- ACCIONES EN INVENTARIO INTELIGENTE ---
    $(document).on('click', '.btn-activar-inventario', function() {
        var btn = $(this);
        var id = btn.data('id');
        btn.prop('disabled', true);
        $.post('/api/producto/accion_masiva/', {
            ids: id,
            accion: 'activo',
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        }, function(resp) {
            if(resp.status === 'ok') {
                btn.closest('tr').find('.label').removeClass('label-default label-info').addClass('label-success').text('Activo');
                btn.prop('disabled', true);
                btn.siblings('.btn-desactivar-inventario').prop('disabled', false);
            } else {
                alert('Error: ' + (resp.msg || 'Error desconocido'));
                btn.prop('disabled', false);
            }
        });
    });
    $(document).on('click', '.btn-desactivar-inventario', function() {
        var btn = $(this);
        var id = btn.data('id');
        btn.prop('disabled', true);
        $.post('/api/producto/accion_masiva/', {
            ids: id,
            accion: 'inactivo',
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        }, function(resp) {
            if(resp.status === 'ok') {
                btn.closest('tr').find('.label').removeClass('label-success label-info').addClass('label-default').text('Inactivo');
                btn.prop('disabled', true);
                btn.siblings('.btn-activar-inventario').prop('disabled', false);
            } else {
                alert('Error: ' + (resp.msg || 'Error desconocido'));
                btn.prop('disabled', false);
            }
        });
    });
    $(document).on('click', '.btn-eliminar-inventario', function() {
        var btn = $(this);
        var id = btn.data('id');
        if(!confirm('¿Está seguro que desea eliminar este producto del inventario?')) return;
        $.post('/api/producto/eliminar/', {
            id: id,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        }, function(resp) {
            if(resp.status === 'ok') {
                btn.closest('tr').fadeOut(400, function(){ $(this).remove(); });
            } else {
                alert('Error al eliminar: ' + (resp.msg || 'Error desconocido'));
            }
        });
    });
    $(document).on('click', '.btn-ver-inventario', function() {
        console.log('CLICK VER INVENTARIO');
        var btn = $(this);
        var row = btn.closest('tr');
        var nombre = row.find('td:eq(0)').text();
        var marca = row.find('td:eq(1)').text();
        var proveedor = row.find('td:eq(2)').text();
        var stock = row.find('td:eq(3)').text();
        var estado = row.find('td:eq(4)').find('span').text();
        var estadoRaw = row.find('td:eq(4)').find('span').text().toLowerCase();
        // Buscar imagen en la celda de la imagen si existe
        var imagen = row.find('img').attr('src') || row.data('imagen') || '/static/imgProductos/placeholder.png';
        // Imagen
        $('#detalleInventarioImagen').attr('src', imagen);
        // Nombre
        $('#detalleInventarioNombre').text(nombre + (marca ? ' ('+marca+')' : ''));
        // Stock
        var stockLabel = $('#detalleInventarioStock');
        stockLabel.text(stock).removeClass('label-danger label-warning label-success');
        var stockNum = parseInt(stock);
        if(stockNum <= 5) stockLabel.addClass('label-danger');
        else if(stockNum <= 15) stockLabel.addClass('label-warning');
        else stockLabel.addClass('label-success');
        // Estado
        var estadoLabel = $('#detalleInventarioEstado');
        estadoLabel.text(estado).removeClass('label-success label-default label-info');
        if(estadoRaw === 'activo') estadoLabel.addClass('label-success');
        else if(estadoRaw === 'inactivo') estadoLabel.addClass('label-default');
        else estadoLabel.addClass('label-info');
        // Proveedor
        $('#detalleInventarioProveedor').text(proveedor);
        // Ocultar formulario de pedir stock
        $('#formPedirStock').hide();
        $('#msgPedirStock').hide();
        $('#btnPedirStock').show();
        $('#modalDetalleInventario').modal('show');
    });
    // Contactar proveedor (mailto: si hay email, si no, alerta)
    $('#btnContactarProveedor').on('click', function() {
        var proveedor = $('#detalleInventarioProveedor').text();
        // Aquí podrías buscar el email real del proveedor si lo tienes
        var email = '';
        if(email) {
            window.location.href = 'mailto:' + email + '?subject=Consulta%20de%20stock';
        } else {
            alert('No hay email registrado para el proveedor: ' + proveedor);
        }
    });
    // Mostrar formulario de pedir stock
    $('#btnPedirStock').on('click', function() {
        $('#formPedirStock').show();
        $(this).hide();
    });
    // Enviar solicitud de stock (simulado)
    $('#formPedirStock').on('submit', function(e) {
        e.preventDefault();
        var cantidad = $('#inputCantidadStock').val();
        var comentario = $('#inputComentarioStock').val();
        $('#msgPedirStock').removeClass('alert-danger').addClass('alert-success').text('Solicitud enviada al proveedor.').show();
        setTimeout(function(){
            $('#modalDetalleInventario').modal('hide');
        }, 1200);
    });

    // Mostrar botón Confirmar al editar precio o stock en línea
    $(document).on('input', '.input-cambio-rapido[data-campo="precio"], .input-cambio-rapido[data-campo="stock"]', function() {
        var row = $(this).closest('tr');
        // Oculta todos los botones confirmar de otras filas
        $('.btn-confirmar-cambio').hide();
        // Muestra solo el de esta fila
        row.find('.btn-confirmar-cambio').show();
    });

    // Mostrar botón Confirmar al cambiar el estado en línea
    $(document).on('change', '.input-cambio-rapido[data-campo="estado"]', function() {
        var row = $(this).closest('tr');
        // Oculta todos los botones confirmar de otras filas
        $('.btn-confirmar-cambio').hide();
        // Muestra solo el de esta fila
        row.find('.btn-confirmar-cambio').show();
    });

    // Handler para el botón Confirmar en edición rápida de precio/stock
    $(document).on('click', '.btn-confirmar-cambio', function() {
        var btn = $(this);
        var row = btn.closest('tr');
        var id = row.data('id');
        var nombre = row.find('td').eq(1).text().trim();
        var proveedor = row.find('td').eq(2).text().trim();
        var precio = row.find('input[data-campo="precio"]').val();
        var stock = row.find('input[data-campo="stock"]').val();
        var estado = row.find('select[data-campo="estado"]').val();
        var csrf = $('input[name="csrfmiddlewaretoken"]').first().val();
        // Validación: el precio debe ser mayor a 0
        if (isNaN(parseFloat(precio)) || parseFloat(precio) <= 0) {
            alert('El precio debe ser mayor a 0.');
            return;
        }
        btn.prop('disabled', true);
        $.ajax({
            url: '/api/producto/editar/',
            method: 'POST',
            data: {
                id: id,
                nombre: nombre,
                proveedor: proveedor,
                precio: precio,
                stock: stock,
                estado: estado,
                csrfmiddlewaretoken: csrf
            },
            success: function(resp) {
                if(resp.status === 'ok') {
                    row.find('input[data-campo="precio"]').val(precio);
                    row.find('input[data-campo="stock"]').val(stock);
                    row.find('select[data-campo="estado"]').val(estado);
                    var stockInput = row.find('input[data-campo="stock"]');
                    var s = parseInt(stock);
                    if (s < 10) {
                        stockInput.css({'background-color':'#f2dede','color':'#a94442'});
                    } else if (s <= 20) {
                        stockInput.css({'background-color':'#fcf8e3','color':'#8a6d3b'});
                    } else {
                        stockInput.css({'background-color':'#dff0d8','color':'#3c763d'});
                    }
                    btn.hide();
                    $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                        '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                        '¡Producto actualizado!'+
                    '</div>').appendTo('body').delay(1500).fadeOut(500, function(){$(this).remove();});
                } else {
                    alert(resp.msg || 'Error al actualizar');
                }
                btn.prop('disabled', false);
            },
            error: function() {
                alert('Error de red al actualizar el producto.');
                btn.prop('disabled', false);
            }
        });
    });

    // ===================== LOGS Y AUDITORÍA =====================
    var logsCargados = false;
    function cargarLogsAuditoria(force) {
        if (logsCargados && !force) return;
        var $tabla = $('#tablaLogsAuditoria tbody');
        var $loader = $('#logsLoader');
        var $vacio = $('#logsVacioRow');
        $tabla.find('tr').not($vacio).remove();
        $vacio.hide();
        $loader.show();
        // Por defecto, ordenar por fecha/hora descendente si no hay filtros activos
        var params = $('#formFiltroLogs').serializeArray();
        var tieneFiltro = params.some(function(p) {
            return p.name !== 'sort' && p.name !== 'dir' && p.value;
        });
        var query = $.param(params);
        if (!tieneFiltro) {
            if (query) query += '&';
            query += 'sort=fecha_hora&dir=desc';
        }
        $.ajax({
            url: '/api/logs/?' + query,
            method: 'GET',
            dataType: 'json',
            success: function(resp) {
                $loader.hide();
                if (resp.logs && resp.logs.length > 0) {
                    resp.logs.forEach(function(log) {
                        var fila = '<tr>' +
                            '<td>' + (log.fecha_hora || '-') + '</td>' +
                            '<td>' + (log.usuario || '-') + '</td>' +
                            '<td>' + (log.accion || '-') + '</td>' +
                            '<td>' + (log.modelo || '-') + '</td>' +
                            '<td>' + (log.detalles || '-') + '</td>' +
                            '</tr>';
                        $tabla.append(fila);
                    });
                } else {
                    $vacio.show();
                }
                logsCargados = true;
            },
            error: function() {
                $loader.hide();
                $tabla.append('<tr><td colspan="5" style="color:#a94442; text-align:center;">Error al cargar los logs.</td></tr>');
            }
        });
    }

    // Al cambiar de pestaña a logs, cargar logs solo si no se han cargado
    $('a[href="#logs"]').on('shown.bs.tab', function() {
        cargarLogsAuditoria();
    });

    // Filtros logs (fuerza recarga)
    $('#formFiltroLogs').on('submit', function(e) {
        e.preventDefault();
        logsCargados = false;
        cargarLogsAuditoria(true);
    });
    $('#btnLimpiarFiltroLogs').on('click', function() {
        $('#formFiltroLogs')[0].reset();
        logsCargados = false;
        cargarLogsAuditoria(true);
    });

    // Si la pestaña logs ya está activa al cargar la página
    if ($('#logs').hasClass('in') && $('#logs').hasClass('active')) {
        cargarLogsAuditoria();
    }
});
// Variables para eliminación individual
var productoAEliminar = null;
var rowAEliminar = null;

// Handler para botón Eliminar individual
$(document).on('click', '.btn-eliminar-producto', function() {
    var btn = $(this);
    var row = btn.closest('tr');
    var id = row.data('id');
    var nombre = row.find('td').eq(1).text();
    productoAEliminar = id;
    rowAEliminar = row;
    $('#nombreProductoEliminar').html(nombre);
    $('#modalConfirmarEliminar .modal-header').css('background', '#d9534f');
    $('#modalConfirmarEliminar .modal-content').css('border', '2px solid #d9534f');
    $('#modalConfirmarEliminar .modal-title').html('<i class="fa fa-exclamation-triangle"></i> Confirmar eliminación');
    $('#modalConfirmarEliminar .modal-body').html('¿Está seguro que desea eliminar el producto <b>' + nombre + '</b>?<br><span style="font-size:13px; color:#a94442;">Esta acción no se puede deshacer.</span>');
    $('#btnConfirmarEliminarProducto').removeClass().addClass('btn btn-danger').text('Eliminar');
    $('#modalConfirmarEliminar').data('masivo', false).data('accion-masiva', false).modal('show');
});
// ===================== CLIENTES Y DISTRIBUIDORES =====================
var clientesCargados = false;
function cargarClientesDistribuidores(force) {
    if (clientesCargados && !force) return;
    var $tabla = $('#tablaClientesDistribuidores tbody');
    var $loader = $('#clientesLoader');
    var $vacio = $('#clientesVacioRow');
    $tabla.find('tr').not($vacio).remove();
    $vacio.hide();
    $loader.show();
    var params = $('#formFiltroClientes').serialize();
    $.ajax({
        url: '/api/clientes/?' + params,
        method: 'GET',
        dataType: 'json',
        success: function(resp) {
            $loader.hide();
            if (resp.clientes && resp.clientes.length > 0) {
                resp.clientes.forEach(function(c) {
                    var fila = '<tr>' +
                        '<td>' + (c.tipo || '-') + '</td>' +
                        '<td>' + (c.nombre || '-') + '</td>' +
                        '<td>' + (c.rut || '-') + '</td>' +
                        '<td>' + (c.email || '-') + '</td>' +
                        '<td>' + (c.telefono || '-') + '</td>' +
                        '<td>' + (c.direccion || '-') + '</td>' +
                        '<td>' + (c.fecha_creacion || '-') + '</td>' +
                        '<td>' + (c.activo ? '<span class="label label-success">Sí</span>' : '<span class="label label-default">No</span>') + '</td>' +
                        '<td><!-- Acciones futuras --></td>' +
                        '</tr>';
                    $tabla.append(fila);
                });
            } else {
                $vacio.show();
            }
            clientesCargados = true;
        },
        error: function() {
            $loader.hide();
            $tabla.append('<tr><td colspan="9" style="color:#a94442; text-align:center;">Error al cargar los clientes.</td></tr>');
        }
    });
}
$('a[href="#clientes"]').on('shown.bs.tab', function() {
    cargarClientesDistribuidores();
});
$('#formFiltroClientes').on('submit', function(e) {
    e.preventDefault();
    clientesCargados = false;
    cargarClientesDistribuidores(true);
});
$('#btnLimpiarFiltroClientes').on('click', function() {
    $('#formFiltroClientes')[0].reset();
    clientesCargados = false;
    cargarClientesDistribuidores(true);
});
if ($('#clientes').hasClass('in') && $('#clientes').hasClass('active')) {
    cargarClientesDistribuidores();
}
// Alta de nuevo cliente/distribuidor
$('#formNuevoClienteDistribuidor').on('submit', function(e) {
    e.preventDefault();
    var form = $(this)[0];
    var data = {
        tipo: $('#nuevoTipo').val(),
        nombre: $('#nuevoNombreCliente').val(),
        rut: $('#nuevoRut').val(),
        email: $('#nuevoEmail').val(),
        telefono: $('#nuevoTelefono').val(),
        direccion: $('#nuevoDireccion').val()
    };
    var btn = $(this).find('button[type="submit"]');
    var errorDiv = $('#nuevoClienteError');
    errorDiv.hide().text("");
    btn.prop('disabled', true);
    $.ajax({
        url: '/api/cliente/nuevo/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(resp) {
            if(resp.status === 'ok') {
                $('#modalNuevoClienteDistribuidor').modal('hide');
                $('<div class="alert alert-success alert-dismissible" role="alert" style="position:fixed;top:20px;right:20px;z-index:9999;min-width:200px;">'+
                    '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ 
                    '¡Cliente/Distribuidor creado con éxito!'+
                '</div>').appendTo('body').delay(2000).fadeOut(500, function(){$(this).remove();});
                clientesCargados = false;
                cargarClientesDistribuidores(true);
            } else {
                errorDiv.text(resp.msg || 'Error desconocido').show();
            }
            btn.prop('disabled', false);
        },
        error: function() {
            errorDiv.text('Error de red al crear el cliente/distribuidor.').show();
            btn.prop('disabled', false);
        }
    });
});
// ===================== PEDIDOS Y VENTAS =====================
var pedidosCargados = false;
function cargarPedidosVentas(force) {
    if (pedidosCargados && !force) return;
    var $tabla = $('#tablaPedidosVentas tbody');
    var $loader = $('#pedidosLoader');
    var $vacio = $('#pedidosVacioRow');
    $tabla.find('tr').not($vacio).remove();
    $vacio.hide();
    $loader.show();
    var params = $('#formFiltroPedidos').serialize();
    $.ajax({
        url: '/api/pedidos/?' + params,
        method: 'GET',
        dataType: 'json',
        success: function(resp) {
            $loader.hide();
            if (resp.pedidos && resp.pedidos.length > 0) {
                resp.pedidos.forEach(function(p) {
                    var productos = (p.items || []).map(function(i){
                        return i.producto__nombre + ' x' + i.cantidad;
                    }).join('<br>');
                    var fila = '<tr>' +
                        '<td>' + (p.fecha ? p.fecha.substring(0, 16).replace('T',' ') : '-') + '</td>' +
                        '<td>' + (p.cliente || '-') + '</td>' +
                        '<td>' + (p.tipo || '-') + '</td>' +
                        '<td>' + (productos || '-') + '</td>' +
                        '<td>$' + (p.total || '0') + '</td>' +
                        '<td>' + (p.estado || '-') + '</td>' +
                        '<td><!-- Acciones futuras --></td>' +
                        '</tr>';
                    $tabla.append(fila);
                });
            } else {
                $vacio.show();
            }
            pedidosCargados = true;
        },
        error: function() {
            $loader.hide();
            $tabla.append('<tr><td colspan="7" style="color:#a94442; text-align:center;">Error al cargar los pedidos.</td></tr>');
        }
    });
}
$('a[href="#pedidos"]').on('shown.bs.tab', function() {
    cargarPedidosVentas();
});
$('#formFiltroPedidos').on('submit', function(e) {
    e.preventDefault();
    pedidosCargados = false;
    cargarPedidosVentas(true);
});
$('#btnLimpiarFiltroPedidos').on('click', function() {
    $('#formFiltroPedidos')[0].reset();
    pedidosCargados = false;
    cargarPedidosVentas(true);
});
if ($('#pedidos').hasClass('in') && $('#pedidos').hasClass('active')) {
    cargarPedidosVentas();
}
// ===================== RESUMEN GENERAL =====================
function cargarResumenGeneral() {
    $.ajax({
        url: '/api/dashboard-resumen/',
        method: 'GET',
        dataType: 'json',
        success: function(resp) {
            $('#resumenTotalProductos').text(resp.total_productos ?? '-');
            $('#resumenTotalPedidos').text(resp.total_pedidos ?? '-');
            $('#resumenTotalClientes').text(resp.total_clientes ?? '-');
            $('#resumenStockBajo').text(resp.stock_bajo ?? '-');
        },
        error: function() {
            $('#resumenTotalProductos, #resumenTotalPedidos, #resumenTotalClientes, #resumenStockBajo').text('-');
        }
    });
}
$('a[href="#resumen"]').on('shown.bs.tab', function() {
    cargarResumenGeneral();
});
if ($('#resumen').hasClass('in') && $('#resumen').hasClass('active')) {
    cargarResumenGeneral();
}
