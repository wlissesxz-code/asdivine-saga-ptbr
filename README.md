# Asdivine Saga — Tradução PT-BR (patch de fãs)

Tradução para o português do Brasil de **Asdivine Saga** (PC, Unity/IL2CPP), com:

- **Tela cheia** (Alt+Enter) habilitada;
- **Menus, interface, itens, missões, ajuda/tutorial e toda a história** traduzidos (~6.000 falas e ~4.300 textos de interface);
- **Acentuação completa** (á à â ã é ê í ó ô õ ú ü ç) desenhada na própria fonte do jogo — ou, se preferir, modo **sem acentos**;
- Instalação **reversível** (um comando restaura o jogo original).

> Este repositório **não contém nenhum arquivo do jogo**. O instalador lê a *sua* cópia do jogo e aplica as traduções (arquivos `data/*.json`) nela. É preciso ter o jogo legalmente. Projeto de fãs, sem vínculo com EXE-CREATE / KEMCO.

## Como instalar (Windows)

1. Instale o [Python 3.9+](https://www.python.org/downloads/) (marque **Add Python to PATH**).
2. Baixe este repositório (**Code → Download ZIP**) e extraia **dentro da pasta do jogo** (a que contém `Asdivine Saga_Data`), ou em qualquer lugar.
3. Feche o jogo e execute **`Instalar.bat`**. Escolha:
   - `1` Português **com acentos** (recomendado)
   - `2` Português sem acentos
   - `3` Somente tela cheia (jogo continua em inglês)
   - `4` Restaurar o jogo original
   - `5` Verificar compatibilidade (não altera nada)
4. Se o instalador não achar o jogo, ele pergunta a pasta (ou use `python ptbr_cli.py instalar --jogo "D:\Jogos\Asdivine Saga"`).

Linux/Steam Deck/macOS: `pip install -r requirements.txt` e `python3 ptbr_cli.py instalar --jogo "/caminho/Asdivine Saga"`.

O instalador guarda backups e o necessário para desfazer em `PTBR_backup/` (dentro da pasta do jogo). **Não apague essa pasta** se quiser poder restaurar; caso contrário use "Verificar integridade" da Steam/GOG Galaxy.

> Se você usou uma versão antiga deste patch (pasta `Patch_PTBR`), rode o `Restaurar.bat` antigo antes de instalar esta.

## Compatibilidade

Testado na versão **GOG** (Unity 2021.3.35f1, IL2CPP). O instalador **procura os textos pelo conteúdo em inglês** (não por posições fixas), então versões levemente diferentes (Steam, atualizações) tendem a funcionar, e ele avisa quando muitas falas não casam. Antes de instalar, a opção **5 / `verificar`** mostra quantas falas/textos foram reconhecidos sem gravar nada. Se der algo diferente de ~100%, abra uma *issue* com a saída.

## Problemas conhecidos / limites

- Não há seletor de idioma dentro do jogo (o patch troca o idioma inteiro; use a opção 4 para voltar ao inglês).
- Algumas mensagens de sistema (baús, lojas) foram abreviadas para caber no mesmo tamanho do original (o script compartilhado é referenciado por posição, então não pode crescer).
- Nomes próprios, monstros, créditos e licenças das fontes permanecem em inglês.
- Textos desenhados em imagens (se houver) não são alterados.

## Se der tela preta ou erro

1. Rode `Instalar.bat` → `4` (restaurar) para voltar ao normal.
2. Abra uma *issue* com: versão do jogo (GOG/Steam), a saída do `Instalar.bat` e o `Player.log` (`%USERPROFILE%\AppData\LocalLow\<empresa>\Asdivine Saga\Player.log`).

## Como funciona (resumo)

- `ptbr/historia.py` — decodifica os scripts de diálogo (`emstr_*` em `resources.assets`), troca o texto inglês pelo PT-BR (quebra linhas conforme a largura real da fonte do jogo) e recalcula os saltos internos do script.
- `ptbr/fonte.py` — compõe os glifos acentuados a partir das letras/sinais da fonte do jogo, grava numa área vazia do atlas e redireciona 25 caracteres CJK raros ("stand-ins"); `moji_hash`/`emoji_hash` recebem os códigos correspondentes.
- `ptbr/meta.py` — traduz literais de `global-metadata.dat` (interface, itens, ajuda) por valor e habilita tela cheia em `globalgamemanagers`.
- `ptbr/unityfile.py` — edições in-place e dados anexados ao final de `resources.assets` (reversível byte a byte).

## Contribuindo com a tradução

Os textos estão em `data/`:

| arquivo | conteúdo |
|---|---|
| `falas_simples.json` | `{"inglês": "português"}` das falas de diálogo |
| `falas_complexas.json` | falas com códigos de controle: `[[linhas EN], [linhas PT]]` (mesmo nº de linhas) |
| `mensagens_sistema.json` | `[índice, "trecho EN", "PT"]` — PT não pode ser maior (em bytes) que o trecho original |
| `literais.json` | textos de interface (`exatos` e `aparados`) |
| `acentos.json` | acento → caractere "stand-in" |

Mantenha os marcadores `%...%`, `{0}`, `$..$` etc. exatamente como no original. Caracteres permitidos: ASCII e `áàâãéêíóôõúüç ÁÀÂÃÉÊÍÓÔÕÚÇ`.

## English summary

Fan translation (Brazilian Portuguese) for *Asdivine Saga* (PC, Unity IL2CPP). The repo ships **no game files**: `Instalar.bat` / `python ptbr_cli.py instalar --jogo <game dir>` reads your own install and patches it (reversible via `restaurar`). Use `verificar` to check compatibility with your version without writing anything. Translations are plain JSON in `data/` (English → Portuguese), so the same tool/approach can be reused for other languages.

## Licença

Código: MIT. Textos de tradução: uso livre para fins não comerciais, com crédito. *Asdivine Saga* e seus assets pertencem aos respectivos titulares.
