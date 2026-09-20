import { Fragment, ReactNode } from 'react'

interface AssistantMarkdownProps {
  content: string
}

function inlineContent(text: string, keyPrefix: string): ReactNode[] {
  const tokenPattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\n]+\*)/g
  const nodes: ReactNode[] = []
  let lastIndex = 0

  for (const match of text.matchAll(tokenPattern)) {
    const index = match.index ?? 0
    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index))
    }

    const token = match[0]
    const key = `${keyPrefix}-${index}`
    if (token.startsWith('**')) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith('`')) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>)
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>)
    }
    lastIndex = index + token.length
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex))
  }

  return nodes
}

function isBlockStart(line: string): boolean {
  return (
    /^#{1,4}\s+/.test(line) ||
    /^[-*]\s+/.test(line) ||
    /^\d+\.\s+/.test(line) ||
    /^-{3,}$/.test(line.trim())
  )
}

function paragraph(lines: string[], key: string): ReactNode {
  return (
    <p key={key}>
      {lines.map((line, index) => (
        <Fragment key={`${key}-line-${index}`}>
          {index > 0 ? <br /> : null}
          {inlineContent(line, `${key}-inline-${index}`)}
        </Fragment>
      ))}
    </p>
  )
}

export function AssistantMarkdown({ content }: AssistantMarkdownProps) {
  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()
    if (!trimmed) {
      index += 1
      continue
    }

    if (/^-{3,}$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${index}`} />)
      index += 1
      continue
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed)
    if (heading) {
      const level = heading[1].length <= 2 ? 3 : 4
      const children = inlineContent(heading[2], `heading-${index}`)
      blocks.push(
        level === 3 ? (
          <h3 key={`heading-${index}`}>{children}</h3>
        ) : (
          <h4 key={`heading-${index}`}>{children}</h4>
        ),
      )
      index += 1
      continue
    }

    const unordered = /^[-*]\s+(.+)$/.exec(trimmed)
    if (unordered) {
      const items: string[] = []
      while (index < lines.length) {
        const match = /^[-*]\s+(.+)$/.exec(lines[index].trim())
        if (!match) break
        items.push(match[1])
        index += 1
      }
      blocks.push(
        <ul key={`ul-${index}`}>
          {items.map((item, itemIndex) => (
            <li key={`ul-${index}-${itemIndex}`}>
              {inlineContent(item, `ul-${index}-${itemIndex}`)}
            </li>
          ))}
        </ul>,
      )
      continue
    }

    const ordered = /^\d+\.\s+(.+)$/.exec(trimmed)
    if (ordered) {
      const items: string[] = []
      while (index < lines.length) {
        const match = /^\d+\.\s+(.+)$/.exec(lines[index].trim())
        if (!match) break
        items.push(match[1])
        index += 1
      }
      blocks.push(
        <ol key={`ol-${index}`}>
          {items.map((item, itemIndex) => (
            <li key={`ol-${index}-${itemIndex}`}>
              {inlineContent(item, `ol-${index}-${itemIndex}`)}
            </li>
          ))}
        </ol>,
      )
      continue
    }

    const paragraphLines = [line]
    index += 1
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index].trim())) {
      paragraphLines.push(lines[index])
      index += 1
    }
    blocks.push(paragraph(paragraphLines, `paragraph-${index}`))
  }

  return <>{blocks}</>
}
