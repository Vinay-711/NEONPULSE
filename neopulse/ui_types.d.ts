declare module 'react' {
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useRef<T>(initialValue?: T): { current: T };
  export function useState<T>(initialState: T | (() => T)): [T, (newState: T | ((prevState: T) => T)) => void];
  export type FC<P = {}> = (props: P) => any;
  const React: any;
  export default React;
}

declare module 'react-native' {
  export const View: any;
  export const Text: any;
  export const StyleSheet: any;
  export const TouchableOpacity: any;
  export const Animated: any;
  export const Easing: any;
  export const SafeAreaView: any;
  export const ScrollView: any;
  export const TouchableWithoutFeedback: any;
  export const Dimensions: any;
}

declare module 'react-native-haptic-feedback' {
  const ReactNativeHapticFeedback: any;
  export default ReactNativeHapticFeedback;
}

declare module 'victory-native' {
  export const VictoryChart: any;
  export const VictoryLine: any;
  export const VictoryAxis: any;
  export const VictoryTheme: any;
}

declare module 'react-native-vector-icons/FontAwesome5' {
  const Icon: any;
  export default Icon;
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module 'react-native-vision-camera' {
  export const Camera: any;
  export const useCameraDevices: any;
}

declare module 'expo-av' {
  export const Audio: any;
}

declare module 'react-native-svg' {
  const Svg: any;
  export const Path: any;
  export const G: any;
  export const Rect: any;
  export default Svg;
}

// Global node types
declare var require: any;

declare module 'expo-speech' {
  export const speak: any;
  export const stop: any;
}

declare module '@react-native-async-storage/async-storage' {
  const AsyncStorage: any;
  export default AsyncStorage;
}

declare module 'firebase/firestore' {
  export const getFirestore: any;
  export const collection: any;
  export const query: any;
  export const orderBy: any;
  export const limit: any;
  export const onSnapshot: any;
  export const doc: any;
  export const setDoc: any;
}

declare module 'recharts' {
  export const LineChart: any;
  export const Line: any;
  export const XAxis: any;
  export const YAxis: any;
  export const CartesianGrid: any;
  export const Tooltip: any;
  export const Legend: any;
  export const ResponsiveContainer: any;
}

declare module '@react-native-community/netinfo' {
  const NetInfo: any;
  export default NetInfo;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
