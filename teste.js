Ext.define('EAM.custom.trigger_python_wsemps', {
    extend: 'EAM.custom.AbstractExtensibleFramework',
    getSelectors: function () {
        return {
            '[extensibleFramework] [tabName=HDR]': {
                aftersaverecord: function () {
                    var vFormPanel = EAM.Utils.getCurrentTab().getFormPanel();
                    var vEmpCode = vFormPanel.getFldValue('employeecode');
                    var vMobile = vFormPanel.getFldValue('mobilephoneno');

                    if (!Ext.isEmpty(vMobile)) {
                        EAM.Ajax.request({
                            // AQUI: URL do seu projeto no Render
                            url: 'https://eam-z-api.onrender.com/iniciar-ativacao',
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            // Enviando o número para o seu FastAPI
                            jsonData: {
                                "numero_master": vMobile
                            },
                            success: function (response) {
    // Transforma a resposta do FastAPI em objeto
    var result = Ext.decode(response.responseText);
    var codigo = result.codigo_gerado;

    Ext.Msg.prompt('Ativação', 'Código gerado: ' + codigo + '<br>Digite o código para confirmar:', function(btn, text) {
        if (btn == 'ok' && text) {
            // Segue a chamada para finalizar-ativacao...
            EAM.Ajax.request({
                url: 'https://eam-z-api.onrender.com/finalizar-ativacao',
                method: 'POST',
                jsonData: {
                    "numero_master": vMobile,
                    "codigo_sms": text
                },
                success: function(resp) {
                    Ext.Msg.alert('Sucesso', 'WhatsApp ativado com sucesso!');
                },
                failure: function(resp) {
                    Ext.Msg.alert('Erro', 'Código inválido.');
                }
            });
        }
    });
},
                            failure: function (response) {
                                console.error('Falha na ativação:', response.status);
                                Ext.Msg.alert('Erro', 'Não foi possível iniciar a ativação.');
                            }
                        });
                    }
                }
            }
        };
    }
});