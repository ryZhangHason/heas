%% wscpaperproc.cls — Local approximation of WSC proceedings class
%% Matches the visual format of WSC 2025/2026 papers.
%% Replace with the official class from the WSC Authors Kit before submission.
%%
%% Specs matched:
%%   Letter paper (8.5 x 11 in), two-column body, single-column title block
%%   11pt Times, title bold ALL CAPS centered, sections bold ALL CAPS numbered

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{wscpaperproc}[2026/01/01 WSC Proceedings (local approximation)]

\LoadClass[11pt,twocolumn,letterpaper]{article}

\RequirePackage{mathptmx}
\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage{geometry}
\RequirePackage{titlesec}
\RequirePackage{url}
\RequirePackage{microtype}

%% Page geometry
\geometry{
  letterpaper,
  top=1.0in, bottom=1.0in,
  left=0.8125in, right=0.8125in,
  columnsep=0.25in,
  headheight=0pt, headsep=0pt, footskip=0pt
}

\pagestyle{empty}

%% Redefine \and so \@author expands without embedded tabulars
\renewcommand{\and}{\par\vspace{0.5em}}

%% Title: bold, ALL CAPS, centered, 12pt
\renewcommand{\maketitle}{%
  \begin{center}
    {\large\bfseries\MakeUppercase{\@title}\par}%
    \vspace{0.8em}
    {\normalsize\@author\par}%
  \end{center}%
  \vspace{0.5em}%
}

%% Author commands
\newcommand{\authorname}[1]{\textbf{#1}}
\newcommand{\authoraddr}[1]{#1}
\newcommand{\authoremail}[1]{\textit{#1}}

%% Section formatting: bold ALL CAPS numbered
\titleformat{\section}
  {\normalfont\normalsize\bfseries}
  {\thesection}{0.75em}{\MakeUppercase}
\titleformat{\subsection}
  {\normalfont\normalsize\bfseries}
  {\thesubsection}{0.75em}{}
\titleformat{\subsubsection}
  {\normalfont\normalsize\itshape}
  {\thesubsubsection}{0.75em}{}
\titlespacing*{\section}   {0pt}{1.0ex plus 0.5ex}{0.4ex}
\titlespacing*{\subsection}{0pt}{0.8ex plus 0.3ex}{0.3ex}

%% Paragraph
\setlength{\parindent}{0.2in}
\setlength{\parskip}{0pt}

%% Abstract handled inline in paper.tex (inside \twocolumn[...])

%% Biography environment
\newenvironment{biography}[1]{%
  \vspace{0.5em}\par\noindent
  \begingroup\small\textbf{#1}\ }%
  {\endgroup\par}

\endinput
