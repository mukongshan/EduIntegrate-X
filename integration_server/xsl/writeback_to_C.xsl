<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <WritebackRequest>
      <meta>
        <sourceCollegeId><xsl:value-of select="/WritebackRequest/meta/sourceCollegeId"/></sourceCollegeId>
        <targetCollegeId><xsl:value-of select="/WritebackRequest/meta/targetCollegeId"/></targetCollegeId>
        <status><xsl:value-of select="/WritebackRequest/meta/status"/></status>
        <requestTime><xsl:value-of select="/WritebackRequest/meta/requestTime"/></requestTime>
      </meta>
      <choices>
        <choice>
          <sid><xsl:value-of select="/WritebackRequest/choices/choice/sid"/></sid>
          <cid><xsl:value-of select="/WritebackRequest/choices/choice/cid"/></cid>
          <score><xsl:value-of select="/WritebackRequest/choices/choice/score"/></score>
        </choice>
      </choices>
    </WritebackRequest>
  </xsl:template>
</xsl:stylesheet>
