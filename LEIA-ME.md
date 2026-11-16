# Site AstroByte

```
index.html        abre direto a realidade aumentada
ar/               10 experiências de realidade aumentada
jogo/             jogo de navegador "Corrida Estelar"
  fotos/          fotos opcionais das cartas do jogo (veja abaixo)
comum/            logo, estilo e céu estrelado usados pelas páginas
```

Para publicar, envie a pasta inteira (com essa estrutura) para o GitHub Pages ou para a hospedagem de vocês. Os links do menu já apontam uns para os outros.

## Jogo: Corrida Estelar

- Toque ou espaço: impulso do jato. Toque rápido = pulo baixo; segurar = pulo alto. Seta para baixo ou deslizar: descer rápido. P: pausar.
- As estrelas douradas abrem cartas com objetos reais. Os textos ficam na lista `CARTAS`, no começo do script do `jogo/index.html`.
- **Fotos:** para mostrar uma foto em vez da ilustração em pixel art, coloque a imagem em `jogo/fotos/` com o nome indicado em cada carta (por exemplo `barnard.jpg`). Usem imagens com licença livre, como as da NASA, e citem a fonte no campo `fonte`.
- Nada é salvo: ao recarregar a página, recorde e cartas recomeçam.

# Realidade aumentada: o universo na sua câmera

Dez experiências de realidade aumentada que abrem pelo navegador, sem instalar nada:

| # | Experiência | Link direto |
|---|---|---|
| 1 | SPHEREx | `ar/#spherex` |
| 2 | Spitzer em tamanho real | `ar/#spitzer` |
| 3 | O céu inteiro | `ar/#ceu` |
| 4 | Os 8 planetas | `ar/#sistema-solar` |
| 5 | Terra e Lua | `ar/#terra-lua` |
| 6 | Marte | `ar/#marte` |
| 7 | Júpiter e as luas de Galileu | `ar/#jupiter` |
| 8 | Saturno | `ar/#saturno` |
| 9 | Órbitas do Planeta X | `ar/#planeta-x` |
| 10 | Tamanho do Planeta X | `ar/#tamanho` |

Cada experiência mostra um título, uma frase, três dados rápidos e uma dica para a câmera. O resto fica guardado em **Saiba mais**.

Tudo é animado: os planetas giram, as luas orbitam, Sedna percorre a órbita dela e os planetas têm um brilho que pulsa devagar. Dentro do 3D há textinhos curtos (nomes e um cartão por cena) que aparecem na câmera.

## Como funciona em cada celular

- **Android (Chrome):** abre a câmera dentro da própria página (WebXR). Aparecem o texto de orientação no topo, os pontos amarelos clicáveis e as animações. Se o aparelho não tiver WebXR, abre o Scene Viewer do Google.
- **iPhone/iPad (Safari):** abre o AR Quick Look da Apple com os arquivos `.usdz`, que já trazem a animação e os textinhos. Os pontos amarelos clicáveis não aparecem no iPhone.
- A realidade aumentada só funciona em endereço **https**.

## Menu, jogo e site parceiro

O menu tem quatro links e aparece igual nas três páginas (em cada `index.html`):


- **Site parceiro:** fica separado por um traço, com a etiqueta "Parceiro". Para ativar, em cada uma das três páginas, troquem `href="#"` pelo endereço, o texto "Site parceiro" pelo nome do site e apaguem `data-pending` da mesma linha.

As redes sociais e o e-mail estão no rodapé (`<footer>`), no fim do `index.html`.

## Integrar em outro site

**Opção 1 (recomendada): copiar os arquivos.** Coloque `index.html` e a pasta `modelos` (com os `.glb` e os `.usdz`) dentro do site de vocês, por exemplo em `/ar/`. Os links ficam `seusite.com/ar/#marte` e assim por diante.

**Opção 2: incorporar com iframe.**

```html
<iframe src="https://SEU-ENDERECO/astrobyte-ar/#jupiter"
        allow="xr-spatial-tracking; fullscreen; camera"
        style="width:100%; height:90vh; border:0"></iframe>
```

Dentro de iframe, alguns celulares (principalmente iPhone) podem não abrir a câmera. Por isso, coloquem também um botão comum com o link para a página.

Para hospedar de graça: GitHub Pages (repositório público, **Settings > Pages**, branch `main`, pasta raiz).

## De onde vêm os dados

- **NASA 3D Resources** (github.com/nasa/NASA-3D-Resources): texturas de Vênus, Marte, Júpiter, Saturno, Netuno, Plutão, Io, Europa, Ganimedes, Calisto, mapa estelar Tycho, foto da Lua da missão Apollo e o modelo oficial do Spitzer.
- **Blue Marble Next Generation (NASA)**, obtida pelo repositório do NASA WorldWind: textura da Terra.
- **NASA Planetary Fact Sheet**: dados dos planetas nas fichas.
- **Feito pela equipe:** o modelo do SPHEREx (simplificado), as texturas de Mercúrio, Urano e do Planeta X, os anéis de Saturno, os textinhos 3D, o brilho e as animações.
- **Órbitas do Planeta X:** valores aproximados. Confiram no JPL Small-Body Database (ssd.jpl.nasa.gov) antes de apresentar.

## Editar os textos

Todo o texto da página está em `SCENES`, dentro do `index.html`. Os textinhos que aparecem **dentro do 3D** estão no `gerar_modelos.py` (procure por `card_image` e `label`).

## Gerar os modelos de novo

```
pip install numpy pillow usd-core
python3 gerar_modelos.py   # cria os .glb (Android e navegador)
python3 gerar_usdz.py      # cria os .usdz animados (iPhone)
```

O primeiro script lê as imagens da pasta `texturas` e grava os `.glb` em `modelos`. O segundo converte cada `.glb` em `.usdz`. Sempre que mudar um modelo, rode os dois. Depois, copie o conteúdo de `modelos/rotulos.json` para a linha `const HOTSPOTS = ...` do `index.html` se mudar a posição de algum ponto clicável.

## Idioma (PT/EN)

Todas as páginas têm os botões **PT | EN** no topo (no jogo, na barra de cima). A escolha fica salva no navegador, e também dá para abrir direto em inglês com `?lang=en` no fim do link (por exemplo `ar/?lang=en#marte`).

- Os textos fixos usam `data-i18n="chave"`. As traduções ficam no próprio `index.html` de cada página, em `AB.registrar({pt:{...}, en:{...}})`.
- Na realidade aumentada, as 10 experiências em inglês estão em `SCENES_EN`. No jogo, as cartas estão em `CARTAS_EN`.
- Os textinhos gravados **dentro** dos modelos 3D continuam em português.

## Acessibilidade

O botão com o ícone de pessoa, ao lado do idioma, abre o painel com estas opções:
- tamanho do texto, em 4 níveis;
- alto contraste;
- reduzir movimento, que para as estrelas, as animações e o giro dos modelos 3D;
- fonte mais legível;
- sublinhar links;
- ouvir o texto da página em voz alta.

As escolhas ficam salvas no navegador. Tudo isso está em `comum/ferramentas.js`.

## SPHEREx · Planeta X (espaço do parceiro)

O link "Parceiro" do menu agora abre `spherex/`, com:
- **Mapa do céu interativo:** feito com o Aladin Lite, com imagens em luz visível (DSS2), infravermelho próximo (2MASS) e infravermelho médio (AllWISE, NASA).
- **Busca:** por nome do objeto ou por coordenadas (AR/Dec em graus ou em h m s).
- **Busca de anomalias no SIMBAD:** objetos com movimento próprio alto, anãs marrons, estrelas variáveis, estrelas jovens, novas, supernovas e anãs brancas.
- **Gráficos:** eventos por tipo, histograma do movimento próprio, mapa dos eventos e quanto os objetos mais rápidos andam em 10 anos.
- **Downloads:** recorte de imagem em JPG ou dados científicos em FITS (via hips2fits do CDS) e o mapa em PNG.
- **Link para o parceiro:** um botão que abre o SPHEREx Sky Explorer do parceiro.

Esses serviços são externos (CDS/Strasbourg). Se algum estiver fora do ar, a página mostra um aviso e o restante continua funcionando.
