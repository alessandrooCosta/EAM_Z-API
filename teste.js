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
                                console.log('Sucesso! SMS enviado pela Z-API.');
                                // Opcional: abrir uma janela para o usuário digitar o código
                                Ext.Msg.alert('Sucesso', 'Código SMS enviado para ' + vMobile);
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