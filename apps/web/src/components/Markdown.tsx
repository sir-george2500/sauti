import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders lesson grammar_md — GFM so noun-class tables work. */
export function Markdown({ source }: { source: string }) {
  return (
    <div className="prose-grammar" data-testid="grammar-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: (props) => (
            <div className="table-wrap">
              <table {...props} />
            </div>
          ),
          a: (props) => (
            <a {...props} className="text-accent-deep underline underline-offset-2" />
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
