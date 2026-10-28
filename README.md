# Dashboard de Monitoramento de Tráfego de Rede

Aplicação didática em **Python + Streamlit + Pandas + Plotly** para analisar o *snapshot* de tráfego fornecido na disciplina **Administração e Gerenciamento de Redes**.

O visual mantém a proposta do projeto anterior de monitoramento ARP: indicadores, gráficos, tabelas, filtros e relatório ao clicar em uma linha. O arquivo `previsualizacao_offline.html` permite abrir uma prévia dos gráficos diretamente no navegador, mesmo antes de instalar o Streamlit; essa prévia não possui os filtros globais do painel completo. **A diferença é que este projeto analisa um arquivo CSV; ele não executa `arp -a` nem monitora a rede em tempo real.**

## 1. Dados recebidos

- Arquivo de origem: `dados_monitoramento_trafego_rede.xlsx` (planilha fornecida para a atividade).
- Arquivo escolhido para este projeto: `dados/trafego_rede.csv`.
- **2.000 registros**, **15 colaboradores**, **12 departamentos** e **23 campos**.
- Registros de **28/10/2026**, entre **07:00:36** e **19:59:52**.
- **1.737 ALLOWED**, **88 ALERT** e **175 BLOCKED**.
- **100 registros de risco Alto**, todos também marcados `BLOCKED` (não somar como 275 incidentes distintos).

> **Observação sobre o enunciado:** o texto entregue informa 8 setores, mas o próprio arquivo apresenta 12 valores distintos em `department`. O programa usa os 12 presentes na base.

## 2. Funcionalidades implementadas

| Exigência | Como foi implementada |
|---|---|
| Top 10 usuários por consumo | Gráfico de barras horizontais, ordenado pela soma do volume em MB |
| Consumo por departamento | Gráfico de barras com todos os departamentos presentes |
| Upload versus download | Gráfico de rosca comparando bytes enviados e recebidos |
| Top destinos e categorias | Domínios mais acessados por quantidade de sessões; categorias por volume; tabela de destinos |
| Incidentes e bloqueios | Tabela interativa com filtro padrão `BLOCKED` **OU** `Alto`, busca textual, filtros adicionais e exportação |

Extras: cartões de KPI, taxa de bloqueio, tráfego por hora, distribuição das ações, filtros globais por departamento/usuário/categoria/risco/protocolo/data/hora, upload de outro CSV, seleção de linha e download de relatório HTML.

## 3. Execução rápida no Windows 11

### Alternativa A — mais simples: duplo clique

1. Extraia **todo o ZIP** para uma pasta, mantendo `app.py`, `analise.py`, `relatorio.py` e o subdiretório `dados` juntos.
2. Tenha o **Python 3.10+** instalado e disponível pelo comando `py`.
3. Dê um duplo clique em **`iniciar_dashboard.bat`**.
4. Na primeira execução, o script cria `.venv` e instala as bibliotecas. É necessário acesso à internet **somente para instalar os pacotes**, não para analisar o CSV local.
5. Acesse **http://localhost:8501** no navegador, caso não abra automaticamente.
6. Para encerrar, volte à janela do terminal e pressione **Ctrl + C**.

### Alternativa B — usando VS Code / PowerShell

Abra **Arquivo → Abrir Pasta** no VS Code, selecione `Dashboard_Monitoramento_Rede`, clique em **Terminal → Novo Terminal** e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

> Não é necessário executar `Activate.ps1` nem liberar scripts no PowerShell. O navegador acessará o Streamlit em `http://localhost:8501`.

### Caso o comando `py -m venv .venv` falhe

Se aparecer erro de `ensurepip`, confira `py --version`, tente `python -m venv .venv` ou use outra versão instalada do Python (de preferência **3.12**). Como alternativa sem ambiente virtual:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py --server.address 127.0.0.1
```

A alternativa sem `.venv` instala as dependências no ambiente Python escolhido e pode requerer permissões/configuração apropriadas.

## 4. Como usar o dashboard

1. Abra a primeira aba **Visão geral** para ver indicadores, Top 10, departamentos, upload/download e tráfego por hora.
2. Acesse **Destinos e categorias** para conferir quais domínios geram mais registros e quais categorias concentram o volume.
3. Na aba **Segurança e incidentes**, examine as sessões bloqueadas ou de risco alto. Utilize o filtro **Tipo de ocorrência** para diferenciar registros `BLOCKED`, `Alto` e `ALERT`.
4. Clique numa linha da tabela para detalhar o evento. O botão **Baixar relatório do evento** gera um arquivo `.html` que pode ser aberto no navegador; pressione **Ctrl + P** para imprimir ou salvar como PDF.
5. Para atualizar a análise, substitua `dados/trafego_rede.csv` por um novo CSV de mesma estrutura ou use o botão **Substituir CSV** na barra lateral. O arquivo original é mantido na pasta do usuário; o upload apenas altera a base analisada na sessão.

**Filtros:** quando uma lista está vazia, considera todos os valores desse campo. Os filtros globais afetam todos os gráficos, KPIs e tabelas, inclusive os incidentes.

## 5. Como explicar os cálculos ao professor

- **Conexões:** quantidade de linhas do arquivo, após os filtros.
- **Usuários:** contagem dos `user_id` diferentes.
- **Departamento:** contagem de setores diferentes.
- **Tráfego total:** soma de `total_bytes` dividida por `1024²` para exibir MB (tecnicamente MiB).
- **Top 10 usuários:** soma de `total_bytes` por `user_name`, ordenada em ordem decrescente.
- **Consumo por setor:** soma dos bytes por `department`.
- **Upload/download:** soma de `bytes_sent` versus soma de `bytes_received`.
- **Top domínios:** contagem das sessões por `dest_domain` (e `category`), ordenada por quantidade de acessos registrados.
- **Categorias:** soma de volumes por `category`.
- **Incidentes:** registros com `action == "BLOCKED"` **ou** `threat_risk == "Alto"`. A operação lógica **OU** impede contar duas vezes o mesmo evento.
- **Taxa de bloqueio:** `100 × conexões BLOCKED / total de conexões filtradas`.

O programa calcula volumes usando **bytes originais**, em vez de somar a coluna `total_megabytes`, pois os valores por linha dessa coluna já estão arredondados. `GB` nos cartões é calculado dividindo os MB exibidos por 1024 (tecnicamente GiB).

### Limitações e interpretação

1. **Não há tempo real**: o CSV é uma fotografia do período informado.
2. **Volume registrado ≠ consumo efetivo comprovado**: sessões marcadas `BLOCKED` podem conter contadores de bytes no registro; o programa não assume que esses dados foram efetivamente transferidos.
3. A relação upload/download, isoladamente, **não comprova saturação**; isso exigiria informações como capacidade do enlace, duração e taxas ao longo do tempo.
4. `Alto`, `BLOCKED` e `ALERT` são rótulos da base: não comprovam, isoladamente, comprometimento ou ato indevido de colaborador.
5. A base apresenta classificações de risco e ações de firewall/proxy, não resultados de inspeção de pacotes.

## 6. Organização dos arquivos

```text
Dashboard_Monitoramento_Rede/
├── app.py                    # Interface, gráficos e filtros Streamlit
├── analise.py                # Carregamento, validação, métricas e agrupamentos
├── relatorio.py              # Exportação do relatório individual em HTML
├── dados/
│   └── trafego_rede.csv      # Snapshot selecionado como fonte
├── tests/
│   └── test_analise.py       # 6 testes automáticos
├── .streamlit/
│   └── config.toml           # Tema visual escuro
├── .gitignore                # Evita .venv e dados sensíveis no Git
├── requirements.txt         # Dependências
├── iniciar_dashboard.bat     # Abertura no Windows
├── previsualizacao_offline.html # Prévia offline (sem filtros globais)
├── README.md                 # Guia de uso
```

## 7. Executar os testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O programa de testes confere quantidade de sessões/usuários/departamentos, incidentes sem duplicidade, soma de bytes, ranking, filtros e escaping HTML.

## 8. Privacidade, publicação e GitHub

O CSV contém logins de usuários, IPs e endereços MAC. Mesmo sendo um exercício, evite publicar os dados em repositórios públicos sem autorização e/ou anonimização adequada. O `.gitignore` exclui `dados/*.csv` de novos commits, além de `.venv` e caches. **Ao clonar um repositório sem o CSV, será preciso colocar o arquivo `dados/trafego_rede.csv` novamente na pasta.**

No computador, a aplicação escuta somente `127.0.0.1` no exemplo, evitando exposição pela rede por padrão. Se colocar o aplicativo em um servidor, configure autenticação/autorização e proteção do arquivo de dados antes de disponibilizá-lo.

## 9. Resumo para apresentação oral

> Desenvolvi um dashboard em Python utilizando Streamlit para a interface, Pandas para tratamento dos dados e Plotly para criar gráficos interativos. O programa importa os 2.000 registros de tráfego de um arquivo CSV, agrupa os dados por usuário, departamento, destino e categoria, apresenta a proporção de uploads e downloads, e identifica conexões bloqueadas ou classificadas como risco alto. Os filtros atualizam todos os indicadores, e é possível selecionar uma ocorrência para gerar um relatório individual. A aplicação analisa registros históricos e não realiza captura em tempo real.
