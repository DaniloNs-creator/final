<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Abas com Gravação</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .tab-header {
            display: flex;
            background-color: #2c3e50;
            overflow-x: auto;
        }
        
        .tab-btn {
            flex: 1;
            min-width: 120px;
            padding: 15px 20px;
            background: none;
            border: none;
            color: #ecf0f1;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            position: relative;
        }
        
        .tab-btn:hover {
            background-color: #34495e;
        }
        
        .tab-btn.active {
            background-color: #3498db;
            color: white;
        }
        
        .tab-btn.completed::after {
            content: "✓";
            position: absolute;
            right: 10px;
            color: #2ecc71;
            font-weight: bold;
        }
        
        .tab-content {
            padding: 30px;
            display: none;
            animation: fadeIn 0.5s;
        }
        
        .tab-content.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #34495e;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            border-color: #3498db;
            outline: none;
            box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
        }
        
        .btn-container {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        
        .btn-prev {
            background-color: #95a5a6;
            color: white;
        }
        
        .btn-prev:hover {
            background-color: #7f8c8d;
        }
        
        .btn-next, .btn-save {
            background-color: #3498db;
            color: white;
        }
        
        .btn-next:hover, .btn-save:hover {
            background-color: #2980b9;
        }
        
        .btn-send {
            background-color: #2ecc71;
            color: white;
        }
        
        .btn-send:hover {
            background-color: #27ae60;
        }
        
        .btn:disabled {
            background-color: #bdc3c7;
            cursor: not-allowed;
        }
        
        .status-message {
            padding: 10px;
            margin-top: 15px;
            border-radius: 5px;
            text-align: center;
            font-weight: 500;
        }
        
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .progress-container {
            margin-bottom: 20px;
            background-color: #ecf0f1;
            border-radius: 5px;
            height: 10px;
        }
        
        .progress-bar {
            height: 100%;
            background-color: #3498db;
            border-radius: 5px;
            width: 0%;
            transition: width 0.5s;
        }
        
        @media (max-width: 768px) {
            .tab-btn {
                min-width: 100px;
                padding: 12px 10px;
                font-size: 14px;
            }
            
            .tab-content {
                padding: 20px;
            }
            
            .btn-container {
                flex-direction: column;
                gap: 10px;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="tab-header">
            <button class="tab-btn active" data-tab="dados-pessoais">Dados Pessoais</button>
            <button class="tab-btn" data-tab="endereco">Endereço</button>
            <button class="tab-btn" data-tab="contato">Contato</button>
            <button class="tab-btn" data-tab="documentos">Documentos</button>
            <button class="tab-btn" data-tab="dados-empresa">Dados Empresa</button>
        </div>
        
        <div class="progress-container">
            <div class="progress-bar" id="progress-bar"></div>
        </div>
        
        <!-- Aba Dados Pessoais -->
        <div class="tab-content active" id="dados-pessoais">
            <h2>Dados Pessoais</h2>
            <div class="form-group">
                <label for="nome">Nome Completo</label>
                <input type="text" id="nome" placeholder="Digite seu nome completo">
            </div>
            <div class="form-group">
                <label for="cpf">CPF</label>
                <input type="text" id="cpf" placeholder="Digite seu CPF">
            </div>
            <div class="form-group">
                <label for="data-nascimento">Data de Nascimento</label>
                <input type="date" id="data-nascimento">
            </div>
            <div class="form-group">
                <label for="genero">Gênero</label>
                <select id="genero">
                    <option value="">Selecione</option>
                    <option value="masculino">Masculino</option>
                    <option value="feminino">Feminino</option>
                    <option value="outro">Outro</option>
                    <option value="prefiro-nao-informar">Prefiro não informar</option>
                </select>
            </div>
            <div class="btn-container">
                <div></div> <!-- Espaço vazio para alinhar o botão à direita -->
                <button class="btn btn-save" id="save-pessoais">Gravar</button>
            </div>
            <div id="status-pessoais" class="status-message"></div>
        </div>
        
        <!-- Aba Endereço -->
        <div class="tab-content" id="endereco">
            <h2>Endereço</h2>
            <div class="form-group">
                <label for="cep">CEP</label>
                <input type="text" id="cep" placeholder="Digite seu CEP">
            </div>
            <div class="form-group">
                <label for="logradouro">Logradouro</label>
                <input type="text" id="logradouro" placeholder="Rua, Avenida, etc.">
            </div>
            <div class="form-group">
                <label for="numero">Número</label>
                <input type="text" id="numero" placeholder="Número">
            </div>
            <div class="form-group">
                <label for="complemento">Complemento</label>
                <input type="text" id="complemento" placeholder="Complemento (opcional)">
            </div>
            <div class="form-group">
                <label for="bairro">Bairro</label>
                <input type="text" id="bairro" placeholder="Bairro">
            </div>
            <div class="form-group">
                <label for="cidade">Cidade</label>
                <input type="text" id="cidade" placeholder="Cidade">
            </div>
            <div class="form-group">
                <label for="estado">Estado</label>
                <select id="estado">
                    <option value="">Selecione</option>
                    <option value="AC">Acre</option>
                    <option value="AL">Alagoas</option>
                    <option value="AP">Amapá</option>
                    <option value="AM">Amazonas</option>
                    <option value="BA">Bahia</option>
                    <option value="CE">Ceará</option>
                    <option value="DF">Distrito Federal</option>
                    <option value="ES">Espírito Santo</option>
                    <option value="GO">Goiás</option>
                    <option value="MA">Maranhão</option>
                    <option value="MT">Mato Grosso</option>
                    <option value="MS">Mato Grosso do Sul</option>
                    <option value="MG">Minas Gerais</option>
                    <option value="PA">Pará</option>
                    <option value="PB">Paraíba</option>
                    <option value="PR">Paraná</option>
                    <option value="PE">Pernambuco</option>
                    <option value="PI">Piauí</option>
                    <option value="RJ">Rio de Janeiro</option>
                    <option value="RN">Rio Grande do Norte</option>
                    <option value="RS">Rio Grande do Sul</option>
                    <option value="RO">Rondônia</option>
                    <option value="RR">Roraima</option>
                    <option value="SC">Santa Catarina</option>
                    <option value="SP">São Paulo</option>
                    <option value="SE">Sergipe</option>
                    <option value="TO">Tocantins</option>
                </select>
            </div>
            <div class="btn-container">
                <button class="btn btn-prev" data-tab="dados-pessoais">Anterior</button>
                <button class="btn btn-save" id="save-endereco">Gravar</button>
            </div>
            <div id="status-endereco" class="status-message"></div>
        </div>
        
        <!-- Aba Contato -->
        <div class="tab-content" id="contato">
            <h2>Contato</h2>
            <div class="form-group">
                <label for="telefone">Telefone</label>
                <input type="text" id="telefone" placeholder="(00) 00000-0000">
            </div>
            <div class="form-group">
                <label for="email">E-mail</label>
                <input type="email" id="email" placeholder="seuemail@exemplo.com">
            </div>
            <div class="form-group">
                <label for="celular">Celular</label>
                <input type="text" id="celular" placeholder="(00) 00000-0000">
            </div>
            <div class="btn-container">
                <button class="btn btn-prev" data-tab="endereco">Anterior</button>
                <button class="btn btn-save" id="save-contato">Gravar</button>
            </div>
            <div id="status-contato" class="status-message"></div>
        </div>
        
        <!-- Aba Documentos -->
        <div class="tab-content" id="documentos">
            <h2>Documentos</h2>
            <div class="form-group">
                <label for="rg">RG</label>
                <input type="text" id="rg" placeholder="Número do RG">
            </div>
            <div class="form-group">
                <label for="orgao-emissor">Órgão Emissor</label>
                <input type="text" id="orgao-emissor" placeholder="Órgão emissor do RG">
            </div>
            <div class="form-group">
                <label for="titulo-eleitor">Título de Eleitor</label>
                <input type="text" id="titulo-eleitor" placeholder="Número do título de eleitor">
            </div>
            <div class="form-group">
                <label for="cnh">CNH</label>
                <input type="text" id="cnh" placeholder="Número da CNH">
            </div>
            <div class="btn-container">
                <button class="btn btn-prev" data-tab="contato">Anterior</button>
                <button class="btn btn-save" id="save-documentos">Gravar</button>
            </div>
            <div id="status-documentos" class="status-message"></div>
        </div>
        
        <!-- Aba Dados Empresa -->
        <div class="tab-content" id="dados-empresa">
            <h2>Dados da Empresa</h2>
            <div class="form-group">
                <label for="razao-social">Razão Social</label>
                <input type="text" id="razao-social" placeholder="Razão social da empresa">
            </div>
            <div class="form-group">
                <label for="nome-fantasia">Nome Fantasia</label>
                <input type="text" id="nome-fantasia" placeholder="Nome fantasia da empresa">
            </div>
            <div class="form-group">
                <label for="cnpj">CNPJ</label>
                <input type="text" id="cnpj" placeholder="CNPJ da empresa">
            </div>
            <div class="form-group">
                <label for="cargo">Cargo</label>
                <input type="text" id="cargo" placeholder="Seu cargo na empresa">
            </div>
            <div class="form-group">
                <label for="setor">Setor</label>
                <input type="text" id="setor" placeholder="Setor de atuação">
            </div>
            <div class="btn-container">
                <button class="btn btn-prev" data-tab="documentos">Anterior</button>
                <div>
                    <button class="btn btn-save" id="save-empresa">Gravar</button>
                    <button class="btn btn-send" id="send-all" disabled>Enviar</button>
                </div>
            </div>
            <div id="status-empresa" class="status-message"></div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Elementos das abas
            const tabBtns = document.querySelectorAll('.tab-btn');
            const tabContents = document.querySelectorAll('.tab-content');
            const progressBar = document.getElementById('progress-bar');
            
            // Botões de navegação
            const prevBtns = document.querySelectorAll('.btn-prev');
            const saveBtns = document.querySelectorAll('.btn-save');
            const sendBtn = document.getElementById('send-all');
            
            // Status de gravação de cada aba
            const savedTabs = {
                'dados-pessoais': false,
                'endereco': false,
                'contato': false,
                'documentos': false,
                'dados-empresa': false
            };
            
            // Inicializar abas
            function initTabs() {
                // Adicionar evento de clique para os botões das abas
                tabBtns.forEach(btn => {
                    btn.addEventListener('click', function() {
                        const tabId = this.getAttribute('data-tab');
                        openTab(tabId);
                    });
                });
                
                // Adicionar evento de clique para os botões "Anterior"
                prevBtns.forEach(btn => {
                    btn.addEventListener('click', function() {
                        const tabId = this.getAttribute('data-tab');
                        openTab(tabId);
                    });
                });
                
                // Adicionar evento de clique para os botões "Gravar"
                saveBtns.forEach(btn => {
                    btn.addEventListener('click', function() {
                        const tabId = this.id.replace('save-', '');
                        saveTab(tabId);
                    });
                });
                
                // Adicionar evento de clique para o botão "Enviar"
                sendBtn.addEventListener('click', sendAllData);
                
                // Atualizar barra de progresso
                updateProgressBar();
            }
            
            // Abrir uma aba específica
            function openTab(tabId) {
                // Verificar se a aba anterior foi salva
                const currentTab = document.querySelector('.tab-content.active').id;
                const currentIndex = Array.from(tabContents).findIndex(tab => tab.id === currentTab);
                const targetIndex = Array.from(tabContents).findIndex(tab => tab.id === tabId);
                
                // Se tentando ir para frente, verificar se a aba atual foi salva
                if (targetIndex > currentIndex && !savedTabs[currentTab]) {
                    showStatus(currentTab, 'error', 'Por favor, grave os dados antes de prosseguir.');
                    return;
                }
                
                // Esconder todas as abas
                tabContents.forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Remover classe active de todos os botões
                tabBtns.forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Mostrar a aba selecionada
                document.getElementById(tabId).classList.add('active');
                
                // Ativar o botão da aba selecionada
                document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
                
                // Atualizar barra de progresso
                updateProgressBar();
            }
            
            // Salvar os dados de uma aba
            function saveTab(tabId) {
                // Aqui você normalmente enviaria os dados para o servidor
                // Por enquanto, vamos apenas simular o salvamento
                
                // Simular validação
                const requiredFields = document.querySelectorAll(`#${tabId} input[required], #${tabId} select[required]`);
                let isValid = true;
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.style.borderColor = '#e74c3c';
                    } else {
                        field.style.borderColor = '#ddd';
                    }
                });
                
                if (!isValid) {
                    showStatus(tabId, 'error', 'Por favor, preencha todos os campos obrigatórios.');
                    return;
                }
                
                // Simular salvamento (em um caso real, aqui seria uma chamada AJAX)
                setTimeout(() => {
                    savedTabs[tabId] = true;
                    
                    // Marcar a aba como concluída
                    const tabBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
                    tabBtn.classList.add('completed');
                    
                    // Mostrar mensagem de sucesso
                    showStatus(tabId, 'success', 'Dados gravados com sucesso!');
                    
                    // Atualizar barra de progresso
                    updateProgressBar();
                    
                    // Habilitar botão "Enviar" se todas as abas foram salvas
                    if (Object.values(savedTabs).every(status => status)) {
                        sendBtn.disabled = false;
                    }
                    
                    // Se não for a última aba, ir para a próxima
                    if (tabId !== 'dados-empresa') {
                        const currentIndex = Array.from(tabContents).findIndex(tab => tab.id === tabId);
                        const nextTab = tabContents[currentIndex + 1].id;
                        openTab(nextTab);
                    }
                }, 1000);
            }
            
            // Enviar todos os dados
            function sendAllData() {
                // Verificar se todas as abas foram salvas
                if (!Object.values(savedTabs).every(status => status)) {
                    alert('Por favor, grave todas as abas antes de enviar.');
                    return;
                }
                
                // Simular envio (em um caso real, aqui seria uma chamada AJAX)
                sendBtn.disabled = true;
                sendBtn.textContent = 'Enviando...';
                
                setTimeout(() => {
                    alert('Todos os dados foram enviados com sucesso!');
                    sendBtn.textContent = 'Enviar';
                    
                    // Aqui você poderia redirecionar o usuário ou limpar o formulário
                }, 2000);
            }
            
            // Mostrar mensagem de status
            function showStatus(tabId, type, message) {
                const statusElement = document.getElementById(`status-${tabId}`);
                statusElement.textContent = message;
                statusElement.className = `status-message ${type}`;
                
                // Remover a mensagem após 5 segundos
                setTimeout(() => {
                    statusElement.textContent = '';
                    statusElement.className = 'status-message';
                }, 5000);
            }
            
            // Atualizar barra de progresso
            function updateProgressBar() {
                const savedCount = Object.values(savedTabs).filter(status => status).length;
                const totalTabs = Object.keys(savedTabs).length;
                const progress = (savedCount / totalTabs) * 100;
                
                progressBar.style.width = `${progress}%`;
            }
            
            // Inicializar o sistema de abas
            initTabs();
        });
    </script>
</body>
</html>