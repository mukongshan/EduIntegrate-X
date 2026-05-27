<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <WithdrawWritebackRequest>
      <enrollmentId><xsl:value-of select="/WithdrawWritebackRequest/enrollmentId"/></enrollmentId>
      <studentId><xsl:value-of select="/WithdrawWritebackRequest/studentId"/></studentId>
      <courseId><xsl:value-of select="/WithdrawWritebackRequest/courseId"/></courseId>
      <status><xsl:value-of select="/WithdrawWritebackRequest/status"/></status>
    </WithdrawWritebackRequest>
  </xsl:template>
</xsl:stylesheet>
