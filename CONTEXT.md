# PDFCrawler — Domain Model

## Ubiquitous Language

**PDF** — Um arquivo portátil com metadados extraíveis (título, autor, número de páginas, datas).

**Caminho completo** — O caminho absoluto do PDF no sistema de arquivos (ex: `/home/user/Docs/folder/file.pdf`). É a identidade única do arquivo no disco.

**Pasta de busca** — Diretório raiz onde o app procura PDFs. O usuário conhece o caminho de antemão.

**Pasta de destino** — Diretório onde os PDFs selecionados serão copiados. Escolhida pelo usuário no momento da cópia.

**Cópia recente** — Uma pasta de busca que o usuário selecionou nas últimas sessões. Acesso rápido sem digitar o caminho.

**Critério de filtro** — Regra que decide se um PDF é relevante:
- **Limite de páginas** — PDFs com mais páginas que este valor são excluídos.
- **Limite de tamanho** — PDFs maiores que este valor são excluídos.

**Arquivo encontrado** — Um PDF que existe na pasta de busca, antes de qualquer validação.

**Arquivo validado** — Um PDF encontrado que passa na validação (abre corretamente, tem metadados legíveis).

**Entrada PDF** — O registro de um arquivo validado: caminho completo, tamanho, hash, páginas, metadados, e se é duplicata.

**Hash** — Digest xxHash64 do conteúdo do arquivo. Usado para detecção de duplicatas.

**Duplicata** — Um arquivo validado cujo hash já foi visto. Não é um erro — é uma proteção contra cópia redundante. A entrada permanece na lista mas é marcada.

**Pesquisa** — A operação de descobrir e validar PDFs em uma pasta de busca.

**Cópia** — A operação de copiar entradas selecionadas para a pasta de destino.

**Operação** — Termo genérico para pesquisa ou cópia em andamento.

## Fluxo principal

1. Usuário informa a **pasta de busca** (campo de texto + seletor + cópias recentes).
2. Usuário aplica **critérios de filtro** (páginas, tamanho).
3. Usuário inicia **pesquisa**.
4. App exibe **entradas PDF** em tabela com busca integrada.
5. Usuário revisa os resultados (pode ver duplicatas marcadas).
6. Usuário clica "Copiar para..." → escolhe **pasta de destino** → inicia **cópia**.
7. Entradas marcadas como duplicata são puladas automaticamente.

## Decisões de design (grilling session)

### Fluxo principal
1. Usuário informa a **pasta de busca** (campo de texto + seletor + cópias recentes).
2. Usuário aplica **critérios de filtro** (páginas, tamanho) — ambos são **mínimos**.
3. Usuário inicia **pesquisa**.
4. App exibe **entradas PDF** em tabela com busca integrada.
5. Usuário revisa e **seleciona manualmente** os itens (com "marcar todos" e "desmarcar todos").
6. Usuário clica "Copiar para..." → escolhe **pasta de destino** (com pastas frequentes) → inicia **cópia**.
7. Entradas marcadas como duplicata são puladas automaticamente.

### Interface
- **Tabela**: ☐ | Título | Autor | Páginas | Tamanho | Caminho relativo
- **Ordenação padrão**: tamanho decrescente
- **Colunas clicáveis** para reordenar
- **Arquivos inválidos**: na tabela com ícone ⚠ e linha riscada
- **Barra de progresso**: determinística com contador ("23/42")
- **Barra de status (rodapé)**: resumo (encontrados, duplicatas, selecionados, tamanho total)
- **Tema**: alternância clara/escuro
- **Janela**: tamanho fixo bom, redimensionável

### Ações
- **Cancelar**: botão durante operação, para após completar item atual
- **Confirmação de cópia**: só pergunta sobre sobrescrever se houver conflito de nomes
- **Notificações**: messagebox (não bloqueia o fluxo, usuário já conhece)

### Atalhos de teclado
- `Ctrl+F` — foco no campo de busca do app
- `Ctrl+O` — abrir seletor de pasta de busca
- `Ctrl+C` — iniciar cópia
- `Ctrl+E` — exportar CSV
- `Enter` — iniciar pesquisa (quando campo de pasta está focado)
- `Espaço` — marcar/desmarcar item selecionado na tabela
- `Ctrl+A` — marcar todos

### Filtros
- **Limite de páginas**: mínimo (ex: ">5" = mais que 5 páginas)
- **Limite de tamanho**: mínimo (ex: ">1MB" = mais que 1 MB)

### Exportar CSV
Campos: título, autor, páginas, tamanho (legível), caminho completo, duplicata (sim/não), hash.
