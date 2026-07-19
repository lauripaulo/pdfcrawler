# Plano de Implementação — Redesign UI/UX do PDFCrawler

**Data**: 2026-07-19  
**Status**: Planejamento concluído (grilling session)  
**Branch**: `refactor/ui-redesign`

---

## Objetivo

Redesign completo da interface do PDFCrawler para melhorar usabilidade e seguir melhores práticas de design para aplicativos desktop, mantendo a arquitetura existente (engine.py com Finder deep module).

---

## Decisões de Design (resumo)

### Fluxo principal
1. Usuário informa a **pasta de busca** (campo de texto + seletor + cópias recentes)
2. Usuário aplica **critérios de filtro** (páginas, tamanho) — ambos são **mínimos**
3. Usuário inicia **pesquisa**
4. App exibe **entradas PDF** em tabela com busca integrada
5. Usuário revisa e **seleciona manualmente** os itens (com "marcar todos" e "desmarcar todos")
6. Usuário clica "Copiar para..." → escolhe **pasta de destino** (com pastas frequentes) → inicia **cópia**
7. Entradas marcadas como duplicata são puladas automaticamente

### Interface
- **Tabela**: ☐ | Título | Autor | Páginas | Tamanho | Caminho relativo
- **Ordenação padrão**: tamanho decrescente
- **Colunas clicáveis** para reordenar
- **Arquivos inválidos**: na tabela com ícone ⚠ e linha riscada
- **Barra de progresso**: determinística com contador ("23/42")
- **Barra de status (rodapé)**: resumo (encontrados, duplicatas, selecionados, tamanho total)
- **Tema**: alternância clara/escuro
- **Janela**: tamanho fixo bom (1280×800), redimensionável

### Ações
- **Cancelar**: botão durante operação, para após completar item atual
- **Confirmação de cópia**: só pergunta sobre sobrescrever se houver conflito de nomes
- **Notificações**: messagebox (não bloqueia o fluxo)

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

---

## Estrutura de Arquivos

```
pdfcrawler/
├── pdfcrawler.py          # GUI principal (refatoração completa)
├── engine.py              # Mantido (Finder, PdfEntry, CallBack)
├── test_engine.py         # Testes existentes (100% coverage)
├── test_gui.py            # Novos testes para GUI (se aplicável)
└── CONTEXT.md             # Modelo do domínio (atualizado)
```

---

## Etapas de Implementação

### Etapa 1: Preparação do Ambiente
- [ ] Criar branch `refactor/ui-redesign` a partir de `refactor/deep-module`
- [ ] Verificar que todos os testes existentes passam (`test_engine.py`)
- [ ] Confirmar que o app roda com as dependências atuais

### Etapa 2: Atualizar engine.py (se necessário)
- [ ] Verificar se `PdfEntry` precisa de campos extras para suportar nova tabela
- [ ] Verificar se `Finder.validate_pdfs` precisa de parâmetro de cancelamento
- [ ] Adicionar flag de cancelamento ao `CallBack` (se necessário)
- [ ] Atualizar `find_all_pdf_files` para suportar cancelamento
- [ ] Atualizar `validate_pdfs` para suportar cancelamento
- [ ] Atualizar `copy_files` para suportar cancelamento
- [ ] Corrigir lógica de filtros: mudar de "máximo" para "mínimo"
- [ ] Rodar testes existentes para garantir que nada quebrou

### Etapa 3: Criar pdfcrawler.py (novo design)
- [ ] Criar classe `PDFCrawler` com:
  - [ ] Janela principal (1280×800, redimensionável)
  - [ ] Seção de controles (pasta de busca, filtros, botões)
  - [ ] Seção de progresso (barra determinística + label)
  - [ ] Seção de resultados (tabela com checkbox + busca)
  - [ ] Barra de status no rodapé
- [ ] Implementar seleção de pasta de busca:
  - [ ] Campo de texto
  - [ ] Botão "Browse..."
  - [ ] Combobox com cópias recentes (salvas em JSON)
- [ ] Implementar filtros:
  - [ ] Combobox "Páginas > N" (valores: >5, >10, >20, >50)
  - [ ] Combobox "Tamanho > N" (valores: >1MB, >5MB, >10MB, >50MB)
  - [ ] Checkbox "Detectar duplicatas"
- [ ] Implementar tabela de resultados:
  - [ ] Colunas: ☐ | Título | Autor | Páginas | Tamanho | Caminho relativo
  - [ ] Checkbox na primeira coluna
  - [ ] Busca integrada (campo de texto acima da tabela)
  - [ ] Ordenação por clique no cabeçalho
  - [ ] Ordenação padrão: tamanho decrescente
  - [ ] Arquivos inválidos: ícone ⚠ + linha riscada
  - [ ] Paginação (se necessário para >100 itens)
- [ ] Implementar botões de ação:
  - [ ] "Start Search"
  - [ ] "Cancel" (aparece apenas durante operação)
  - [ ] "Select All" / "Deselect All"
  - [ ] "Copy Selected To..."
  - [ ] "Export CSV"
- [ ] Implementar seleção de pasta de destino:
  - [ ] Campo de texto
  - [ ] Botão "Browse..."
  - [ ] 3-5 pastas frequentes fixadas (salvas em JSON)
- [ ] Implementar tema claro/escuro:
  - [ ] Switch no canto superior direito
  - [ ] Salvar preferência em JSON
- [ ] Implementar atalhos de teclado:
  - [ ] Ctrl+F, Ctrl+O, Ctrl+C, Ctrl+E
  - [ ] Enter (quando campo de pasta focado)
  - [ ] Espaço (marcar/desmarcar item)
  - [ ] Ctrl+A (marcar todos)
- [ ] Implementar cancelamento:
  - [ ] Flag de cancelamento no observer
  - [ ] Verificar flag entre itens no loop
  - [ ] Completar item atual antes de parar

### Etapa 4: Atualizar observers (FileFinderObserver, FileCopyObserver)
- [ ] Adicionar suporte a cancelamento
- [ ] Atualizar progress bar para modo determinístico com contador
- [ ] Atualizar label para mostrar "Processando X/Y..."
- [ ] Adicionar suporte a tema (cores dinâmicas)

### Etapa 5: Persistência de dados
- [ ] Criar classe `SettingsManager`:
  - [ ] Salvar/carregar cópias recentes de pastas de busca (JSON)
  - [ ] Salvar/carregar pastas frequentes de destino (JSON)
  - [ ] Salvar/carregar preferência de tema (JSON)
- [ ] Definir local para salvar configurações (~/.pdfcrawler/settings.json)

### Etapa 6: Testes
- [ ] Adicionar testes para nova lógica de filtros (mínimo)
- [ ] Adicionar testes para cancelamento (se aplicável ao engine)
- [ ] Testes manuais de UI:
  - [ ] Pesquisa funciona corretamente
  - [ ] Filtros de mínimo funcionam
  - [ ] Cancelamento para após item atual
  - [ ] Barra de progresso atualiza corretamente
  - [ ] Seleção manual funciona
  - [ ] "Marcar todos" / "Desmarcar todos" funcionam
  - [ ] Busca na tabela filtra resultados
  - [ ] Ordenação por clique no cabeçalho funciona
  - [ ] Arquivos inválidos aparecem com ⚠ e riscado
  - [ ] Tema claro/escuro alterna corretamente
  - [ ] Atalhos de teclado funcionam
  - [ ] Pastas recentes/frequentes são salvas e carregadas
  - [ ] Confirmação de sobrescrita só aparece em conflito
  - [ ] Barra de status mostra resumo correto
  - [ ] Exportar CSV funciona com novos campos
  - [ ] Copiar selecionados funciona

### Etapa 7: Documentação
- [ ] Atualizar README.md com novas funcionalidades
- [ ] Atualar CONTEXT.md com decisões de design
- [ ] Adicionar comentários no código (se necessário)

---

## Critérios de Aceitação

### Funcionais
- [ ] Usuário pode pesquisar PDFs em uma pasta
- [ ] Filtros de páginas e tamanho funcionam como mínimos
- [ ] Usuário pode cancelar pesquisa/cópia
- [ ] Barra de progresso mostra progresso real (determinística)
- [ ] Usuário pode selecionar manualmente itens na tabela
- [ ] "Marcar todos" e "desmarcar todos" funcionam
- [ ] Busca na tabela filtra resultados
- [ ] Ordenação por clique no cabeçalho funciona
- [ ] Arquivos inválidos aparecem na tabela com indicação visual
- [ ] Barra de status mostra resumo correto
- [ ] Tema claro/escuro alterna corretamente
- [ ] Atalhos de teclado funcionam
- [ ] Pastas recentes/frequentes são salvas e carregadas
- [ ] Confirmação de sobrescrita só aparece em conflito
- [ ] Exportar CSV funciona com novos campos

### Não-funcionais
- [ ] App roda em macOS, Linux, Windows
- [ ] Interface responsiva (não trava durante operações longas)
- [ ] Código segue padrões existentes (engine.py com Finder deep module)
- [ ] Testes existentes ainda passam (100% coverage em engine.py)
- [ ] Código documentado (comentários onde necessário)

---

## Risks e Mitigações

| Risk | Impact | Mitigação |
|------|--------|-----------|
| PyPDF2 data parsing issues | Arquivos inválidos não são exibidos corretamente | Testar com variedade de formatos de data |
| ttkbootstrap 1.20.4 API changes | Widgets não renderizam corretamente | Testar em todas as plataformas |
| Performance com muitos PDFs (>500) | Tabela lenta, UI trava | Implementar lazy loading/paginação se necessário |
| Cancelamento em meio a operações | Estado inconsistente | Testar cancelamento em vários pontos do loop |
| Persistência de settings | Perda de dados ao atualizar | Usar formato JSON simples, fallback para valores padrão |

---

## Ordem de Execução Recomendada

1. **Etapa 1** (5 min) — Preparação do ambiente
2. **Etapa 2** (15 min) — Atualizar engine.py (se necessário)
3. **Etapa 3** (60 min) — Criar pdfcrawler.py (novo design)
4. **Etapa 4** (15 min) — Atualizar observers
5. **Etapa 5** (10 min) — Persistência de dados
6. **Etapa 6** (30 min) — Testes
7. **Etapa 7** (10 min) — Documentação

**Tempo estimado total**: ~2 horas

---

## Commit Strategy

- **Commit 1**: `chore: create ui-redesign branch` — branch a partir de refactor/deep-module
- **Commit 2**: `refactor(engine): support cancellation in find/validate/copy operations` — adicionar flag de cancelamento ao engine
- **Commit 3**: `refactor(engine): change filters from max to min` — corrigir lógica de filtros
- **Commit 4**: `refactor(gui): complete UI redesign with new layout` — novo pdfcrawler.py
- **Commit 5**: `feat(gui): add keyboard shortcuts, theme toggle, persistence` — atalhos, tema, settings
- **Commit 6**: `test: update tests for new filter logic and cancellation` — testes atualizados
- **Commit 7**: `docs: update CONTEXT.md and README with new features` — documentação

---

## Próximos Passos

1. Revisar este plano
2. Confirmar que está tudo correto
3. Executar a implementação na próxima sessão
4. Commit e push após conclusão

---

## Notas Finais

- Manter compatibilidade com ttkbootstrap 1.20.4 (sem bootstyle, padding, text em Frame/LabelFrame)
- Usar código existente do engine.py (Finder, PdfEntry, CallBack)
- Manter 100% de coverage em engine.py
- Testar em todas as plataformas (macOS, Linux, Windows)
- Usar padrão de nomenclatura existente (camelCase para métodos, PascalCase para classes)
