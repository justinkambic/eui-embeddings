import {
  EuiButton,
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
} from "@elastic/eui";
import { iconTypes } from "../util";
export default function IconPage() {
  const icons: JSX.Element[] = iconTypes.map((iconName) => (
    <EuiFlexGroup key={iconName}>
      <EuiFlexItem grow={false}>
        <EuiIcon type={iconName} size="xxl" />
      </EuiFlexItem>
      <EuiFlexItem grow={false}>
        <EuiButton href={`/icon/${iconName}`}>View Icon</EuiButton>
      </EuiFlexItem>
    </EuiFlexGroup>
  ));

  return <EuiFlexGroup direction="column">{icons}</EuiFlexGroup>;
}
