import {
  EuiPageTemplate,
  EuiPage,
  EuiPageBody,
  EuiPageSection,
} from "@elastic/eui";

const maxWidth = 1100;

export default function PageTemplate({ children }) {
  return (
    <EuiPageTemplate offset={0} panelled restrictWidth>
      <EuiPageTemplate.Header
        iconType="logoElastic"
        pageTitle="EUI Icon Semantic Search"
        restrictWidth={maxWidth}
        onClick={() => window.location.assign("/")}
      />
      <EuiPageTemplate.Section restrictWidth={maxWidth} alignment="top" grow>{children}</EuiPageTemplate.Section>
    </EuiPageTemplate>
  );
}
