'use client';

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { GraphNode, GraphEdge, SeedEntityType } from '@/types';
import { useAppStore } from '@/lib/store';

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
}

const ENTITY_COLORS: Record<string, string> = {
  domain: '#00f0ff',
  ip_address: '#10b981',
  email: '#f59e0b',
  person: '#8b5cf6',
  organization: '#38bdf8',
  file_hash: '#f43f5e',
  url: '#ec4899',
  certificate: '#06b6d4',
  asn: '#a855f7',
  phone: '#14b8a6',
};

export const ForceGraphInner: React.FC<Props> = ({ nodes, edges, width, height }) => {
  const fgRef = useRef<ForceGraphMethods<any, any> | undefined>(undefined);
  const { selectedNode, setSelectedNode, setSelectedEdge, graphFilterType } = useAppStore();

  // Filter nodes if an entity type filter is active
  const filteredData = useMemo(() => {
    let filteredNodes = nodes;
    if (graphFilterType) {
      filteredNodes = nodes.filter((n) => n.entity_type === graphFilterType);
    }
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = edges.filter((e) => {
      const srcId = typeof e.source === 'object' ? (e.source as any).id : e.source;
      const tgtId = typeof e.target === 'object' ? (e.target as any).id : e.target;
      return nodeIds.has(srcId) && nodeIds.has(tgtId);
    });

    return {
      nodes: filteredNodes.map((n) => ({ ...n })),
      links: filteredEdges.map((e) => ({ ...e })),
    };
  }, [nodes, edges, graphFilterType]);

  // Auto zoom-to-fit on initial data load
  useEffect(() => {
    if (fgRef.current && filteredData.nodes.length > 0) {
      setTimeout(() => {
        fgRef.current?.zoomToFit(400, 50);
      }, 300);
    }
  }, [filteredData.nodes.length]);

  // Center on selected node
  useEffect(() => {
    if (selectedNode && fgRef.current && selectedNode.x !== undefined && selectedNode.y !== undefined) {
      fgRef.current.centerAt(selectedNode.x, selectedNode.y, 600);
      fgRef.current.zoom(2.5, 600);
    }
  }, [selectedNode]);

  // Custom node canvas renderer
  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = selectedNode?.id === node.id;
      const color = ENTITY_COLORS[node.entity_type] || '#00f0ff';
      const radius = isSelected ? 8 : 6;

      // Outer glow for selected node
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'rgba(0, 240, 255, 0.25)';
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = '#00f0ff';
        ctx.stroke();
      }

      // Main node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();

      // Node Label
      const label = node.label || node.value || node.id;
      const fontSize = Math.max(10 / globalScale, 3.5);
      ctx.font = `${isSelected ? 'bold' : 'normal'} ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Background pill for label text
      const textWidth = ctx.measureText(label).width;
      const textY = node.y + radius + fontSize + 2;

      ctx.fillStyle = 'rgba(6, 9, 17, 0.85)';
      ctx.fillRect(node.x - textWidth / 2 - 3, textY - fontSize / 2 - 2, textWidth + 6, fontSize + 4);

      // Label stroke border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(node.x - textWidth / 2 - 3, textY - fontSize / 2 - 2, textWidth + 6, fontSize + 4);

      // Text itself
      ctx.fillStyle = isSelected ? '#00f0ff' : '#f1f5f9';
      ctx.fillText(label, node.x, textY);
    },
    [selectedNode]
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <ForceGraph2D
        ref={fgRef as any}
        width={width}
        height={height}
        graphData={filteredData}
        backgroundColor="#070b14"
        nodeRelSize={6}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.beginPath();
          ctx.arc(node.x, node.y, 12, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkColor={() => 'rgba(255, 255, 255, 0.18)'}
        linkWidth={1.5}
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => '#00f0ff'}
        linkDirectionalArrowLength={4.5}
        linkDirectionalArrowRelPos={1}
        linkLabel={(link: any) => `${link.relationship_type || 'relates_to'} (${link.confidence || 'observed'})`}
        onNodeClick={(node: any) => {
          setSelectedNode(node);
        }}
        onLinkClick={(link: any) => {
          setSelectedEdge(link);
        }}
        onBackgroundClick={() => {
          setSelectedNode(null);
          setSelectedEdge(null);
        }}
        cooldownTicks={120}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
    </div>
  );
};
