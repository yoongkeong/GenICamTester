import pypylon.genicam as genicam
import logging

logger = logging.getLogger(__name__)

class GenICamHelper:
    def validate_xml(self, camera):
        try:
            xml = camera.GetDeviceInfo().GetXML()
            logger.info("Validating GenICam XML descriptor")
            # Validation logic here (e.g., XML schema check)
            return True
        except genicam.RuntimeException as e:
            logger.error(f"XML Validation failed: {str(e)}")
            return False

    def access_feature(self, camera, feature_name):
        try:
            node_map = camera.GetNodeMap()
            feature_node = node_map.GetNode(feature_name)
            if feature_node.IsReadable:
                logger.info(f"Feature {feature_name} is readable")
                return feature_node.GetValue()
            else:
                logger.warning(f"Feature {feature_name} is not accessible")
                return None
        except Exception as e:
            logger.error(f"Feature access failed: {str(e)}")
            raise e